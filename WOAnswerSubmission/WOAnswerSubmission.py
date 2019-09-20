'''
@Author: <SaqibKhaleel>
Date of creation: 2018:12:28 1:10:11
Purpose of the micro service: <DESCRIPTION BY AUTHOR>
'''

'''
ANY TODO

'''

#IMPORT MODULES
import json
from os import environ
import WOHeader
import db_utility
import pymongo
import datetime
import random
import boto3
#CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
DATABASE_CONNECTION_ERROR = "Failed to insert in the Database"

#TEST EVENT
testEvent = { "body" : {"candidateToken":"mxaawaopld",'questionId':2,'sort_order':4,'answer':{'mcq':[1,2],'videoUrl':"youtube.com","textUrl":"slack.com"}}}
requiredParams = ["candidateToken","questionId",'answer']

def checkAllRequiredValuesPresent(request):
	for param in requiredParams:
		if(param not in request):
			print("The value "+param+" missing")
			return False	
	return True

def validateRequest(request):
	headerValidation = True

	'''
	BOTO3 TO VALUDATE THE HEADER IF NEEDED
	check the environment flag ("isHeaderValidationRequired")
	'''
	if('candidateToken' not in request['body'] and 'testMode' not in request['body'] and environ.get('isHeaderValidationRequired')):
		requestBody = WOHeader.run(request)
		if(requestBody['authenticationCode'] !="200"):
			headerValidation = False
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
		response = {"error":UNAUTHENTICATION_ERROR_MSG,"errorCode":404}
	elif(not checkAllRequiredValuesPresent(requestBody)):
		print(MISSING_ERROR_MSG)
		response = {"error":MISSING_ERROR_MSG, "errorCode":402}
	'''
	BUSINESS LOGIC VALIDATION HERE
	'''
	if "error" not in response:
		response = requestBody
	return response
    
def validateCandidate(requestBody):
	testDetail=db_utility.fetch_where("test",{"token":requestBody['candidateToken']})
	if len(testDetail)==0:
		return False
	else:
		if (testDetail[0]['is_active']):
			orgDetail=db_utility.fetch_where("organization_details",{"organization_id":testDetail[0]['organization_id']})[0]
			if (orgDetail['is_active']):
				questionSetDetail=db_utility.fetch_where("question_set",{"question_set_id":testDetail[0]['question_set_id']})[0]
				if (questionSetDetail['is_active']):
					return True
		else:
			return False


def lambda_handler(event,context):
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] =  {"Access-Control-Allow-Methods":"*", "Access-Control-Allow-Headers":"*", "Access-Control-Allow-Origin":"*"}

	validRequest = validateRequest(event)
	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
	else:
		'''
		BUSINESS LOGIC STARTS HERE
		'''	
		# print(validRequest)
		candidateToken=validRequest['candidateToken']
		testDetail=db_utility.fetch_where("test",{"token":candidateToken})[0]
		testId=testDetail['test_id']
		# questionSetDetail=db_utility.fetch_where("question_set",{"question_set_id":testDetail['question_set_id']})[0]
		# sampleQuestionSetDetails=db_utility.fetch_where("question_set",{"question_set_id":questionSetDetail['sample_question_set_id']})[0]
		# print(sampleQuestionSetDetails['question_list'])
		questionId=validRequest['questionId']
		questionDetail=db_utility.fetch_where('question_master',{'question_id':questionId})[0]
		answer=validRequest['answer']
		print(answer)
		if questionDetail['question_type_id']==1:
			param={}
			param['response_id']=db_utility.fetch_next_id("test_response","response_id")
			param["_id"]=param['response_id']
			param['question_id']=validRequest['questionId']
			param['test_id']=testId
			param['answer_mcq']=answer['mcq']
			param['submitted_at']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		elif questionDetail['question_type_id']==2:
			param={}
			param['response_id']=db_utility.fetch_next_id("test_response","response_id")
			param["_id"]=param['response_id']
			param['question_id']=validRequest['questionId']
			param['test_id']=testId
			if 'videoUrl' in answer:
				param['video_url']=answer['videoUrl']
			if 'textUrl' in answer:
				param['text_url']=answer['textUrl']
			param['submitted_at']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
		data=db_utility.insert_data_one('test_response',param)
		# print("1")
		# print(data)
		if data=="200":
			testQuestionTracker=db_utility.fetch_where_and('test_question_tracker',[{'test_id':testId,'question_id':questionId}])[0]
			param={}
			currentSortOrder=testQuestionTracker['sort_order']
			print(currentSortOrder)
			param=testQuestionTracker
			param['submit_status']=True
			trackerData=db_utility.update_data_one('test_question_tracker',{"question_tracker_id":testQuestionTracker['question_tracker_id']},param)
			# print(data)
		if trackerData=="200":
			param={}
			param['tracker_id']=db_utility.fetch_next_id("log_tracker","tracker_id")
			param['_id']=param['tracker_id']
			param['test_id']=testId
			param['activity_type_id']="004"
			param['activity_time']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			# logData=db_utility.insert_data_one('log_tracker',param)
			logData="200"
		if logData=="200":
			print("Data Inserted")
			# sortOrder=0
			sortOrder=currentSortOrder+1
			print(sortOrder)
			while True:
				nextQuestionId=db_utility.fetch_where('test_question_tracker',{'sort_order':sortOrder,'test_id':testId})				
				if (len(nextQuestionId)>0 and not nextQuestionId[0]['submit_status']):
					nextQuestionId=nextQuestionId[0]['question_id']
					break
				elif (len(nextQuestionId)>0 and nextQuestionId[0]['submit_status'] and sortOrder!=currentSortOrder):
					sortOrder=sortOrder+1
				elif (len(nextQuestionId)==0 and sortOrder!=currentSortOrder):
					sortOrder=1
				elif (len(nextQuestionId)>0 and sortOrder==currentSortOrder):
					nextQuestionId=0
					break
				else:
					nextQuestionId=0
					break
		if nextQuestionId==0:
			param={}
			param['test_ended']=True
		else:
			client = boto3.client('lambda',region_name = environ['Region'])
			# print("Invoking AkriValidateToken micro service to validate token")
			nextQuestion = client.invoke(
			FunctionName='WO-'+environ['stage']+'-LookupQuestion',
			InvocationType='RequestResponse',
			Payload=json.dumps({"body":{'questionId': nextQuestionId,"candidateToken":candidateToken}})
			)
			
			nextQuestion= json.loads(nextQuestion['Payload'].read().decode("utf-8"))
			param={}
			param=nextQuestion['body']
			param=json.loads(param)
			param['sort_order']=sortOrder
			param['test_ended']=False
			print(param)
				
			if len(param)>0:
				print("Data Fetched")
				# param=questionDetail['body']
			else:
				param['statusCode']=400
				param['Error']=DATABASE_CONNECTION_ERROR
		response=param
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''	
		proxyResponse['statusCode'] = 200
		# response={}
		# print(response)
		proxyResponse['body'] = json.dumps(response)
	print(proxyResponse)
	return proxyResponse

# lambda_handler(testEvent,100)

