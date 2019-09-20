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
import WOHeader
import db_utility as db
import datetime
from os import environ
import json
import boto3
import pymongo
import time

#CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
ADMIN = 'admin'
RECRUITER = 'recruiter'
typeOfUsser = None
TABLE_TO_USE = 'candidate'
COUNT = 10
USER_TABLE ='user_master'
USER_GROUP = 'user_group'
#TEST EVENT

requiredParams = ['candidateId']

testEvent = {
	"body": {
		
		'candidateId':0
		},
	"method": "POST",
	"principalId": "",
	"stage": "dev",
	"cognitoPoolClaims": {
		"sub": ""
	},
	"enhancedAuthContext": {},
	"headers": {
		"Accept": "*/*",
		"accept-encoding": "gzip, deflate",
		"Authorization": "adsrtyujkfjhgfd",
		"cache-control": "no-cache",
		"Content-Type": "application/json",
		"Host": "560m86nk1k.execute-api.ap-south-1.amazonaws.com",
		"Postman-Token": "88824333-477e-4074-9336-9dd1f420881a",
		"User-Agent": "PostmanRuntime/7.4.0",
		"X-Amzn-Trace-Id": "Root=1-5c0a18fc-e79a95131567aacd44c973b5",
		"X-Forwarded-For": "115.249.61.61",
		"X-Forwarded-Port": "443",
		"X-Forwarded-Proto": "https"
	},
	"query": {},
	"path": {},
	"identity": {
		"cognitoIdentityPoolId": "",
		"accountId": "",
		"cognitoIdentityId": "",
		"caller": "",
		"sourceIp": "115.249.61.61",
		"accessKey": "",
		"cognitoAuthenticationType": "",
		"cognitoAuthenticationProvider": "",
		"userArn": "",
		"userAgent": "PostmanRuntime/7.4.0",
		"user": ""
	},
	"stageVariables": {}
}


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
		print("userId = ",requestBody['userId'])
		userGroupId = db.fetch_where_and(USER_TABLE, [{'user_name': requestBody['userId']}])[0]['user_group_id']
		print("user group id =  ", userGroupId)
		userGroupName = db.fetch_where_and(USER_GROUP, [{'user_group_id': userGroupId}])[0]['user_group_name']
		print("user group name = ", userGroupName)
		requestBody['userGroup'] = userGroupName
		if userGroupName == RECRUITER:
			requestBody['typeOfUser'] = RECRUITER
			requestBody['organizationId'] = db.fetch_where_and(USER_TABLE,[{'user_name':requestBody['userId']}])[0]['organization_id']
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
	'''
	BUSINESS LOGIC VALIDATION HERE
	'''

	response = requestBody
	return response
def lambda_handler(event,context):
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] =  {"Access-Control-Allow-Methods":"*", "Access-Control-Allow-Headers":"*", "Access-Control-Allow-Origin":"*"}
	validRequest = validateRequest(event)
	print("Valid Request",validRequest)
	try:
		if('error' in validRequest):
			proxyResponse['statusCode'] = validRequest['errorCode']
			proxyResponse['error'] = validRequest['error']
		else:
			'''
			BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
			'''	
			print("BUSINESS LOGIC")
			candidateInformation = db.fetch_where_and(TABLE_TO_USE,[{"candidate_id":validRequest['candidateId']}])
			if(len(candidateInformation)==0):
				print("No candidate found")
				proxyResponse['statusCode'] = 402
				proxyResponse['error'] = "candidate does not exist"
				return proxyResponse
			organizationIdOfCandidate = candidateInformation[0]['organization_id']
			if 'organizationId' in validRequest:
				if(validRequest['organizationId'] != organizationIdOfCandidate):
					print("candidate does not belong to this organization")
					proxyResponse['statusCode'] = 402
					proxyResponse['error'] = "candidate does not belong to this organization"
					return proxyResponse

			candidateDetails = db.fetch_where_and(TABLE_TO_USE,[{"candidate_id":validRequest['candidateId']}])
			print("lenght of candidate list = ",len(candidateDetails))
			print("candidates = ",candidateDetails)

			
			if(len(candidateDetails)>0):
				for  i  in candidateDetails:
					if '_id' in i:
						del i['_id']
				response = candidateDetails
			proxyResponse['statusCode'] = 200
			proxyResponse['body'] = json.dumps(response)
			print("proxyResponse = ",proxyResponse)
			return proxyResponse
	except Exception as e:
		proxyResponse['statusCode'] = 402
		proxyResponse['error'] = "Invaid parameters in request"
	proxyResponse['body'] = json.dumps(response)
	#print(proxyResponse)
	return proxyResponse
#print(lambda_handler(testEvent,"context"))
