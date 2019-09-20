'''
@Author: <SaqibKhaleel>
Date of creation: 2018:12:24 18:05:16
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
#CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
DATABASE_CONNECTION_ERROR = "Failed to insert in the Database"

#TEST EVENT
testEvent = { "body" : {"copy_question_set":True,"question_set_id":1,"userId":"recruiter@workonic.com"}}

requiredParams = ["question_set_id","copy_question_set"]

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
	return 0

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
		userName=validRequest['userId']
		userDetail=db_utility.fetch_where("user_master",{"user_name":userName})[0]
		param={}
		# for i in requiredParams:
		# 	param[i]=validRequest[i]
		
		userGroup=userDetail['user_group_id']
		# print(userGroup)
		if userGroup==2 and validRequest['copy_question_set']:
			existing_param=db_utility.fetch_where('question_set',{'question_set_id':validRequest['question_set_id']})[0]
			print(existing_param)
			param={}
			param['question_set_id']=db_utility.fetch_next_id('question_set','question_set_id')
			param['_id']=param['question_set_id']
			param['question_set_name']=existing_param['question_set_name']
			param['question_list']=existing_param['question_list']
			param['is_sample_set']=existing_param['is_sample_set']
			param['is_question_bank']=False
			if 'expire_at' in existing_param:
				param['expire_at']=existing_param['expire_at']
			param['duration']=existing_param['duration']
			param['is_active']=existing_param['is_active']
			param['is_partial_complete_allowed']=existing_param['is_partial_complete_allowed']
			param['last_updated_at']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			param['is_active']=existing_param['is_active']
			param['is_random_order']=existing_param['is_random_order']
			param['is_show']= True
			param['created_at']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			param['created_by']=userDetail['user_id']
			param['organization_id']=userDetail['organization_id']
			data=db_utility.insert_data_one("question_set",param)
			param['message'] = "Question set copied successfully"
			
		if( not validRequest['copy_question_set']):
			questionSetId = validRequest['question_set_id']
			status = False

			data = db_utility.update_data_one("question_set", 
			{"question_set_id": questionSetId },{"is_show":status})
			param['message'] = "Question set deleted successfully"
			

		else:
			param["statusCode"]=404
			param['Error']=UNAUTHENTICATION_ERROR_MSG

			
		if data=="200":
			print("Data Updated")
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
