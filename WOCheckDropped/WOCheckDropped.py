'''
@Author: <SaqibKhaleel>
Date of creation: 2018:12:10 11:45:13
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
testEvent = { "body" : {"userId":"recruiter@workonic.com"}} #(Take this out while deploying)

requiredParams = []

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

def fetch_last_log(test):
   try:
	   db=db_utility.getDBConnection()
	   collection=db["log_tracker"]
	   data=collection.find({"test_id":test},{"_id":0}).sort("tracker_id",-1).limit(1)
   except Exception as e:
	   print(e)
	   return "401"
   else:
	   return list(data)

def lambda_handler(event,context):
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] =  {"Access-Control-Allow-Methods":"*", "Access-Control-Allow-Headers":"*", "Access-Control-Allow-Origin":"*"}
	validRequest = {}
	# validRequest = validateRequest(event)
	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
	else:
		'''
		BUSINESS LOGIC STARTS HERE
		'''	
		# userName=validRequest['userId']
		# userDetail=db_utility.fetch_where("user_master",{"user_name":userName})[0]
		# param={}
		# userGroup=userDetail['user_group_id']
		# print("UserGroup " +str(userGroup))
		# if userGroup==1:
		# 	activeTest=db_utility.fetch_all("test")
		# elif userGroup==2:
		# 	orgId=userDetail['organization_id']
		# 	activeTest=db_utility.fetch_where("test",{'organization_id':orgId})
		activeTest=db_utility.fetch_all("test")
		if len(activeTest)>0:
			currentTime=datetime.datetime.now()
			print(currentTime)
			timeDiffAllowed=30
			for i in range(len(activeTest)):
				activeTestId=activeTest[i]['test_id']
				# logs=db_utility.fetch_where("log_tracker",{"test_id":activeTestId})
				# param = sorted(logs, key=lambda  k: k['tracker_id'])[-1]
				param=fetch_last_log(activeTestId)[0]
				if param['activity_type_id']=="003" or param['activity_type_id']=="004" or param['activity_type_id']=="008":
					testId=param['test_id']
					data=db_utility.fetch_where("last_user_time",{"test_id":testId})
					if len(data)>0:
						Time=data[0]['log_time']
						testTime=datetime.datetime.strptime(str(Time),"%Y-%m-%dT%H:%M:%S") + datetime.timedelta(seconds=timeDiffAllowed)
						# print(testTime)
					else:
						testTime=currentTime - datetime.timedelta(seconds=timeDiffAllowed)
						# testTime=datetime.datetime.strptime(str(Time),"%Y-%m-%dT%H:%M:%S")
						# print(testTime)
					if currentTime>testTime:
						print(testId)
						param={}
						param['tracker_id']=db_utility.fetch_next_id("log_tracker","tracker_id")
						param['_id']=param['tracker_id']
						param['test_id']=testId
						param['activity_type_id']="444"
						param['activity_time']=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
						print(param)
						data=db_utility.insert_data_one("log_tracker",param)
						# timeDiff=currentTime-testTime
						# print(timeDiff)
					else:
						data="200"
				else:
					data="0"
		if data=="200":
			param={}
			param['statusCode']="200"
			param['message']="Dropped Test Moved To Dropped Category"
		else:
			param={}
			param['statusCode']="200"
			param['message']="No Dropped To Test"
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''	
		proxyResponse['statusCode'] = 200
		response=param
		print(response)
		proxyResponse['body'] = json.dumps(response)
		# print(proxyResponse)
	return proxyResponse

lambda_handler(testEvent,100)
