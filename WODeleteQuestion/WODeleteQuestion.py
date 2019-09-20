'''
@Author: Shameer
Date of creation: 2018:12:07 19:03:01
Purpose of the micro service: Delete category from organisation
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
testEvent = {"body":{"questionId":5,"testMode":1,"userId":"rec@whirdatascience.com"}}

requiredParams = ['questionId']

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
	if('testMode' not in request["body"] and environ.get('isHeaderValidationRequired')):
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
		requestBody["userGroupId"] = userInfo["user_group_id"]
		if(not userInfo["is_active"]) :
			print(MISSING_LOGIC_MSG)
			print("User permission restricted")
			response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
		elif(not db_utility.is_exist("question_master",{"question_id":requestBody["questionId"]})) :
			print(MISSING_LOGIC_MSG)
			print("Question ID does not exist")
			response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
		elif(requestBody["userGroupId"] == 1):
			requestBody["adminId"] = userInfo["admin_id"]
		elif(requestBody["userGroupId"] == 2):
			requestBody["organizationId"] = userInfo["organization_id"]
			if(not fetch_organisation_status(requestBody["organizationId"])):
				print(MISSING_LOGIC_MSG)
				print("Organisation permission restricted")
				response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
			elif(not db_utility.is_exist("question_master",{"question_id":requestBody["questionId"],"organization_id":requestBody["organizationId"]})) :
				print(MISSING_LOGIC_MSG)
				print("User permission restricted")
				response = {"error":MISSING_LOGIC_MSG, "errorCode":402}
	if('error' not in response):
		response = requestBody
	return response

def fetch_user_info(request) :
		data = db_utility.fetch_where("user_master",{"user_name": request["userId"]})
		return data[0]

def fetch_organisation_status(organizationId) :
		data = db_utility.fetch_where("organization_details",{"organization_id": organizationId })
		return data[0]["is_active"]
		
def delete_all(tableName,condition):
    try:
        db=db_utility.getDBConnection()
        collection=db[tableName]
        collection.delete_many(condition)
    except Exception as e:
        print(e)
        return "401"
    else:
        return "200"
        
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
		questionId = validRequest["questionId"]
		
		# data = delete_all("question_master",{"question_id":questionId})
		# data = delete_all("question_category",{"question_id":questionId})
		# data = delete_all("question_mcq",{"question_id":questionId})
		data = db_utility.update_data_one("question_master",{"question_id":questionId},{"is_active":False})
		
		if(data == "200") :
			response["responseCode"] = "200"
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''	
		proxyResponse['statusCode'] = 200
		proxyResponse['body'] = json.dumps(response)
	print(proxyResponse)
	return proxyResponse

# lambda_handler(testEvent,100)

