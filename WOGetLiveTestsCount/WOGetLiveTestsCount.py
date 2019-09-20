'''
@Author: Shameer
Date of creation: 2018:12:07 19:03:01
Purpose of the micro service: Get live test Count
'''

'''
ANY TODO

'''

#IMPORT MODULES
import json
import db_utility
from os import environ
import WOHeader
import datetime

#CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
MISSING_LOGIC_MSG = "Missing required logic in request"

#TEST EVENT
testEvent = {"body":{"organizationId":1,"testMode":1,"userId":"gchandrapandian@whirldatascience.com"}}

requiredParams = []

def checkAllRequiredValuesPresent(request):
	for param in requiredParams:
		if(param not in request):
			return False	
	return True

def validateRequest(request):
	headerValidation = True

	'''
	BOTO3 TO VALIDATE THE HEADER IF NEEDED
	check the environment flag ("isHeaderValidationRequired")
	'''
	if('candidateToken' not in request["body"] and 'testMode' not in request["body"] and environ.get('isHeaderValidationRequired')):
		requestBody = WOHeader.run(request)
		if(requestBody['authenticationCode'] !="200"):
			headerValidation = False
	else:
		requestBody = request['body']

	'''
	VALIDATE CANDIDATE TOKEN
	'''
	# if('candidateToken' in requestBody):
	# 	candidateInfo = validateCandidate(requestBody)
	# 	requestBody['candidate'] = candidateInfo

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
	if('error' not in response):
		userInfo = fetch_user_info(requestBody)
		userGroupId = userInfo["user_group_id"]
		requestBody["userGroup"] = fetch_user_group_name(userGroupId)
		if(not userInfo["is_active"]) :
			print(MISSING_LOGIC_MSG)
			print("User permission restricted")
			response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
		elif("organizationId" in requestBody and not db_utility.is_exist("organization_details",{"organization_id":requestBody["organizationId"]})) :
			print(MISSING_LOGIC_MSG)
			print("Organisation ID does not exist")
			response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
	
	if('error' not in response):
		response = requestBody
	return response

def fetch_user_info(request) :
		data = db_utility.fetch_where("user_master",{"user_name": request["userId"] })
		return data[0]

def fetch_user_group_name(userGroupId) :
		data = db_utility.fetch_where("user_group",{"user_group_id": userGroupId })
		return data[0]["user_group_name"]

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
		
def fetch_live_test_count(tests):
	count = 0
	for test in tests :
		data = fetch_last_log(test["test_id"])
		if(len(data)!=0):
			data = data[0]
			activity = ["003","004","008"]
			if(data["activity_type_id"] in activity):
				count = count + 1
	return count
    

def lambda_handler(event,context):
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] =  {"Access-Control-Allow-Methods":"*", "Access-Control-Allow-Headers":"*", "Access-Control-Allow-Origin":"*"}

	validRequest = validateRequest(event)
	print(validRequest)
	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
	else:
		'''
		BUSINESS LOGIC STARTS HERE
		'''	
		if(validRequest["userGroup"] == "admin") :
			print("ENTERING ADMIN ACTIONS")
			if("organizationId" in validRequest):
				organizationId = validRequest["organizationId"]
				tests = db_utility.fetch_where("test",{"is_active":True,"organization_id":organizationId})
				response["liveTestCount"]=fetch_live_test_count(tests)
			else :
				tests = db_utility.fetch_where("test",{"is_active":True})
				print(tests)
				response["liveTestCount"]=fetch_live_test_count(tests)

		else :
			print("ENTERING RECRUITER ACTIONS")
			organizationId = fetch_user_info(validRequest)["organization_id"]
			tests = db_utility.fetch_where("test",{"is_active":True,"organization_id":organizationId})
			response["liveTestCount"]=fetch_live_test_count(tests)
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''	
		proxyResponse['statusCode'] = 200
		proxyResponse['body'] = json.dumps(response)
	print(proxyResponse)
	return proxyResponse

# lambda_handler(testEvent,100)

