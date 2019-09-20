import math
from dateutil.parser import parse
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
TEST_RESPONSE = 'test_response'
TEST_QUESTION_TRACKER = "test_question_tracker"
STATUS = True
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


def questionAttended(testId):
	questionsAttended = db.fetch_where_and(
		TEST_QUESTION_TRACKER, [{"test_id": testId, "submit_status": STATUS}])
	print("Attended questions = ", questionsAttended)
	return len(questionsAttended)


def findDurationForTest(testId):
    proxyResponse = {}
    testResponses = db.fetch_where_and(TEST_RESPONSE, [{'test_id': testId}])
    if(len(testResponses) <= 0):
        return 0
    sortedList = sorted(testResponses, key=lambda x: x['response_id'])
    print("First one = ", sortedList[-1]['submitted_at'])
    print("Last one = ", sortedList[0]['submitted_at'])
    timeTakenUntilNow = (parse(
    	sortedList[-1]['submitted_at']) - parse(sortedList[0]['submitted_at'])).seconds
    timeTakenInMinutes = math.ceil(timeTakenUntilNow/60)
    print("Time taken in minutes  =", timeTakenInMinutes)
    return timeTakenInMinutes


def lambda_handler(event, context):
	print("Event = ", event)
	if 'Payload' in event:
		oldEvent = event
		event = json.loads(event['Payload'].read().decode("utf-8"))
		print("event from payload =  ", event)
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] = {"Access-Control-Allow-Methods": "*",
                             "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}
	validRequest = validateRequest(event)
	print("Valid Request", validRequest)
	try:
		if('error' in validRequest):
			proxyResponse['statusCode'] = validRequest['errorCode']
			proxyResponse['error'] = validRequest['error']
			return proxyResponse
		else:
			'''
			BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
			'''
			response = {}
			# New updated code on jan 17
			# testResponseDetails = db.fetch_where_and(TEST_RESPONSE,[{"test_id":validRequest['testId']}])
			# print("test response details = ",testResponseDetails)
			# if(len(testResponseDetails) <= 0):
			# 	response['questionAttempted'] = 0
			# 	response['duration'] = 0
			# 	proxyResponse['statusCode'] = 200
			# 	proxyResponse['body'] = json.dumps([response])
			# 	return proxyResponse
			# sortedTestResponseDetails = sorted(testResponseDetails ,key=lambda x:x['response_id'])
			# print("sorted test response details = ",sortedTestResponseDetails)
			# timeTakenUntilNow = (parse(sortedTestResponseDetails[-1]['submitted_at']) - parse(sortedTestResponseDetails[0]['submitted_at'])).seconds
			# print("time taken = ",timeTakenUntilNow)
			# timeTakenInMinutes =  math.ceil(timeTakenUntilNow/60)
			# print("time taken in minutes = ",timeTakenInMinutes)
			# numberOfQuestionsAttempted = len(sortedTestResponseDetails)
			# print("Number of question attempted = ",numberOfQuestionsAttempted)
			numberOfQuestionsAttempted = questionAttended(validRequest['testId'])
			if(numberOfQuestionsAttempted <= 0):
				response['questionAttempted'] = 0
				response['duration'] = 0
				proxyResponse['statusCode'] = 200
				proxyResponse['body'] = json.dumps([response])
				return proxyResponse
			response['questionAttempted'] = numberOfQuestionsAttempted
			response['duration'] = findDurationForTest(validRequest['testId'])
			proxyResponse['statusCode'] = 200
			proxyResponse['body'] = json.dumps([response])
			return proxyResponse
	except Exception as e:
		proxyResponse['statusCode'] = 402
		proxyResponse['error'] = "Error "
		return proxyResponse
	proxyResponse['body'] = json.dumps(response)
	#print(proxyResponse)
	return proxyResponse
#print(lambda_handler(testEvent,"context"))
#"2018-12-11T07:48:02"
