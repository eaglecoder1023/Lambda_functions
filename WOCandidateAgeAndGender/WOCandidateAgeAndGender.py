import math
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
SCORE_TYPE = 'age_range'
GENDER = 'gender'
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
	totalMCQQuestion = test_question_tracker.aggregate_raw_batches([{"$match": {"test_id": validRequest['testId']}}, {"$lookup": {"from": "question_master", "localField": "question_id", "foreignField": "question_id", "as": "question_type"}}, {
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
			high = []
			low = []
			[high.append(i) if(i['label'] == 'High') else low.append(i)
                            for i in questionsAnswered]
			highAgeRange = math.ceil(sum(i['value'] for i in high)/len(high))
			print("HighAgeRange =  ", highAgeRange)
			lowAgeRange = math.ceil(sum(i['value'] for i in low)/len(low))
			print("lowAgeRange =  ", lowAgeRange)
			questionsAnswered = db.fetch_where_and(
				DESC_SCORE, [{"test_id": validRequest['testId'], "key":GENDER}])
			genderList = []
			for i in questionsAnswered:
				genderList.append(i['label'])
			print("genderList = ", genderList)
			genderCount = {i: genderList.count(i) for i in set(genderList)}
			print("genderCount = ", genderCount)
			genderMaxProb = max(genderCount.keys(), key=(lambda x: genderCount[x]))
			print("genderMaxProbability = ", genderMaxProb)
			response['highAgeRange'] = highAgeRange
			response['lowAgeRange'] = lowAgeRange
			response['gender'] = genderMaxProb
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
