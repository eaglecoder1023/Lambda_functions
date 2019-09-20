import bson
import time
import pymongo
import boto3
import json
from os import environ
import datetime
import db_utility as db
import WOHeader
'''
@Author: Gopirengaraj
Date of creation: 2018:12:06 14:03:34
Purpose of the micro service: This microservice will add new organization by the user
'''

'''
ANY TODO
validate token for admin
'''

#IMPORT MODULES
#CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
ADMIN = 'admin'
RECRUITER = 'recruiter'
typeOfUser = None
USER_TABLE = 'user_master'
COUNT = 10
USER_GROUP = 'user_group'
TEST_TABLE = 'test'
QUESTION_SET_LIST = 'question_set_list'
QUESTION_SET = 'question_set'
QUESTION_SCHEME = 'question_scheme'
ORGANIZATION_DETAILS = 'organization_details'
DESC_TYPE_ID = 2
TEST_QUESTION_TRACKER = 'test_question_tracker'
MCQ_SCORE = 'mcq_score'
DESC_SCORE = 'descriptive_score'
SCORE_TYPE = 'sentiment_score'
QUESTION_MASTER = "question_master"
#TEST EVENT

requiredParams = ['testId']


def checkAllRequiredValuesPresent(request):
	for param in requiredParams:
		if(param not in request):
			print("The value "+param+" missing")
			return False
	return True


def validateCandidate(requestBody):
	return {"candidateId:12"}


def validateRequest(request):
	headerValidation = True

	'''
	BOTO3 TO VALUDATE THE HEADER IF NEEDED
	check the environment flag ("isHeaderValidationRequired")
	'''
	if('candidateToken' not in request['body'] and 'testMode' not in request['body'] and environ.get('isHeaderValidationRequired')):
		requestBody = WOHeader.run(request)
		if(requestBody['authenticationCode'] != '200'):
			headerValidation = False
			print(UNAUTHENTICATION_ERROR_MSG)
			response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
			return response
		if(not checkAllRequiredValuesPresent(requestBody)):
			print(MISSING_ERROR_MSG)
			response = {"error": MISSING_ERROR_MSG, "errorCode": 402}
			return response
		#FINDING USER NAME AND ID
		print("userId = ", requestBody['userId'])
		userGroupId = db.fetch_where_and(
			USER_TABLE, [{'user_name': requestBody['userId']}])[0]['user_group_id']
		print("user group id =  ", userGroupId)
		userGroupName = db.fetch_where_and(
			USER_GROUP, [{'user_group_id': userGroupId}])[0]['user_group_name']
		print("user group name = ", userGroupName)
		requestBody['userGroup'] = userGroupName

		if userGroupName == RECRUITER:
			requestBody['typeOfUser'] = RECRUITER
			requestBody['organizationId'] = db.fetch_where_and(
				USER_TABLE, [{'user_name': requestBody['userId']}])[0]['organization_id']
		elif userGroupName == ADMIN:
			# This happens when Admin create a new organization
			if 'organizationId' in requestBody:
				requestBody['typeOfUser'] = RECRUITER
			else:
				requestBody['typeOfUser'] = ADMIN
	else:
		requestBody = request['body']

	'''
	VALIDATE CANDIDATE TOKEN
	'''

	if('candidateToken' in requestBody):
		candidateInfo = validateCandidate(requestBody)
		requestBody['candidate'] = candidateInfo

	response = {}
	if(not headerValidation):
		print(UNAUTHENTICATION_ERROR_MSG)
		response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
	elif(not checkAllRequiredValuesPresent(requestBody)):
		print(MISSING_ERROR_MSG)
		response = {"error": MISSING_ERROR_MSG, "errorCode": 402}
	response = requestBody
	return response


def totalNoOfMCQQuestion(validRequest):
	client = pymongo.MongoClient(
		"mongodb://"+environ['HOSTNAME']+":"+environ['PORT']+"/")
	database = client[environ['DATABASE']]
	test_question_tracker = database[TEST_QUESTION_TRACKER]
	# db.test_question_tracker.aggregate([{"$match":{"test_id":validRequest['testId']}},{"$lookup":{"from":"question_master","localField":"question_id","foreignField":"question_id","as":"question_type"}},{"$unwind":"$question_type"},{"$project":{"_id":0,"question_id":1,"question_type.question_type_id":1}},{"$match":{"question_type.question_type_id":MCQ_TYPE_ID}}])
	totalMCQQuestion = test_question_tracker.aggregate_raw_batches([{"$match": {"test_id": validRequest['testId'], 'submit_status':True}}, {"$lookup": {"from": "question_master", "localField": "question_id", "foreignField": "question_id", "as": "question_type"}}, {
	                                                               "$unwind": "$question_type"}, {"$project": {"_id": 0, "question_id": 1, "question_type.question_type_id": 1, "question_type.score": 1}}, {"$match": {"question_type.question_type_id": DESC_TYPE_ID}}])
	print("BYTE response = ", totalMCQQuestion)
	totalMCQQuestionList = []
	for i in totalMCQQuestion:
		temp = bson.decode_all(i)
		print("temp = ", temp)
		totalMCQQuestionList.append(temp)
	print("questionList = ", totalMCQQuestionList[0])
	questionsAttempted = len(totalMCQQuestionList[0])
	# totalScore = sum(i['question_type']['score'] for i in totalMCQQuestionList[0])
	print("total questions attempted", questionsAttempted)
	client.close()
	# return questionsAttempted,totalScore
	return questionsAttempted


def findingDescQuestionCount(testId):
    descQuestionCount = 0
    allQuestionDetails = db.fetch_where_and(
    	TEST_QUESTION_TRACKER, [{"test_id": testId}])
    for i in allQuestionDetails:
        questionDetails = db.fetch_where_and(
            QUESTION_MASTER, [{"question_id": i['question_id']}])
        if(questionDetails[0]['question_type_id'] == 2):
            descQuestionCount += 1
    print("Total desc question count =", descQuestionCount)
    return descQuestionCount


def lambda_handler(event, context):
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] = {"Access-Control-Allow-Methods": "*",
                             "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}
	validRequest = validateRequest(event)
	print("Valid Request", validRequest)

	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
		return proxyResponse
	else:
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''
		try:
			Negative = 0
			Positive = 0
			Mixed = 0
			Neutral = 0
			Nomatch = 0
			response = {}
			print("Test id = ", validRequest['testId'])
			testStatus = db.is_exist(TEST_TABLE, {"test_id": validRequest['testId']})
			print("test status = ", testStatus, " test status type =", type(testStatus))
			if(not testStatus):
				proxyResponse['statusCode'] = 402
				proxyResponse['error'] = "test not found"
				return proxyResponse
			totalDescQuestions = totalNoOfMCQQuestion(validRequest)
			if(totalDescQuestions == 0):
				response['error'] = "No questions found in the test"
				response['statusCode'] = 402
				return response
			# print("Total score = ",totalScore)
			print("Total question = ", totalDescQuestions)
			questionsAnswered = db.fetch_where_and(
				DESC_SCORE, [{"test_id": validRequest['testId'], "key":SCORE_TYPE}])
			print("Ans question = ", questionsAnswered)
			questionsAnsweredCount = len(questionsAnswered)
			print("Ans count = ", questionsAnsweredCount)
			if(questionsAnsweredCount == 0):
				print("No questions found")
				response['statusCode'] = 200
				response['body'] = json.dumps([])
				return response
			for i in questionsAnswered:
				print("question =  ", i)
				if i['label'] == "Negative":
					print("Negative")
					Negative += 1
				elif i['label'] == "Positive":
					print("Positive")
					Positive += 1
				elif i['label'] == "Neutral":
					print("Neutral")
					Neutral += 1
				elif i['label'] == "Mixed":
					print("Mixed")
					Mixed += 1
				else:
					print("Nomatch")
					Nomatch += 1
			print(Negative, Positive, Neutral, Mixed)
			if(totalDescQuestions > questionsAnsweredCount):
				NegativePercent = int((Negative/questionsAnsweredCount)*100)
				PositivePercent = int((Positive/questionsAnsweredCount)*100)
				MixedPercent = int((Mixed/questionsAnsweredCount)*100)
				NeutralPercent = int((Neutral/questionsAnsweredCount)*100)
				response['totalQuestionInDB'] = int(questionsAnsweredCount)
			else:
				NegativePercent = int((Negative/totalDescQuestions)*100)
				PositivePercent = int((Positive/totalDescQuestions)*100)
				MixedPercent = int((Mixed/totalDescQuestions)*100)
				NeutralPercent = int((Neutral/totalDescQuestions)*100)
				response['totalQuestionInDB'] = int(totalDescQuestions)
			response['NegativePercent'] = NegativePercent
			response['PositivePercent'] = PositivePercent
			response['MixedPercent'] = MixedPercent
			response['NeutralPercent'] = NeutralPercent
			response['totalQuestion'] = findingDescQuestionCount(validRequest['testId'])
			print("response = ", response)
			proxyResponse['statusCode'] = 200
			proxyResponse['body'] = json.dumps(response)
			return proxyResponse
		except Exception as e:
			proxyResponse['statusCode'] = 402
			proxyResponse['error'] = str(e)
			return proxyResponse
		print(proxyResponse)
	return proxyResponse
#print(lambda_handler(testEvent,"context"))
