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
ORGANIZATION_TABLE = "organization_details"
ADMIN = 'admin'
RECRUITER = 'recruiter'
USER_POOL_ID = environ['userpoolid']
USER_TABLE = 'user_master'
USER_GROUP = 'user_group'
CAT_MAT = "category_master"
CAT_ID = "category_id"
requiredParams = ["organizationName", "organizationContactPerson",
                  "organizationContactEmail", "organizationContactMobile",
                  "organizationAddress", "organizationWebsite",
                  "expireDate", "status", "firstName", "lastName"]


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
		print("userId = ", requestBody['userId'])
		userDetails = db.fetch_where_and(
			USER_TABLE, [{'user_name': requestBody['userId']}])[0]
		print("creator details = ", userDetails)
		# userGroupId = /db.fetch_where_and(USER_TABLE, [{'user_name': requestBody['userId']}])[0]['user_group_id']
		userGroupId = userDetails['user_group_id']
		print("userGroup id = ", userGroupId)
		adminId = userDetails['admin_id']
		print("admin id = ", adminId)
		userId = userDetails['user_id']
		print("userId = ", userId)
		if (userDetails['is_active'] == False):
			print(UNAUTHENTICATION_ERROR_MSG)
			response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
			return response
		print("user group id =  ", userGroupId)
		userGroupName = db.fetch_where_and(
			USER_GROUP, [{'user_group_id': userGroupId}])[0]['user_group_name']
		print("user group name = ", userGroupName)
		requestBody['userGroup'] = userGroupName
		if userGroupName == RECRUITER:
			print(UNAUTHENTICATION_ERROR_MSG)
			response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
			return response
		# elif userGroupName == ADMIN:
		# 	# This happens when Admin create a new organization
		# 	if 'organizationId' in requestBody:
		# 		requestBody['typeOfUser'] = RECRUITER
		# 	else:
		# 		requestBody['typeOfUser'] = ADMIN
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
		return response
	elif(not checkAllRequiredValuesPresent(requestBody)):
		print(MISSING_ERROR_MSG)
		response = {"error": MISSING_ERROR_MSG, "errorCode": 402}
		return response
	'''
	BUSINESS LOGIC VALIDATION HERE
	'''

	response = requestBody
	return response


def creatingNewUserForOrganization(event):
	function_name = 'WO-'+environ['stage']+'-Adduser'
	print("Calling function name = ", function_name)
	lambdaCall = boto3.client('lambda', region_name=environ['Region'])
	createUserResponse = lambdaCall.invoke(
		FunctionName=function_name, InvocationType='RequestResponse', LogType='Tail', Payload=json.dumps(event))
	return createUserResponse


def deleteUser(username):
    cognito = boto3.client('cognito-idp', region_name=environ['cognitoregion'])
    deleteUserResponse = cognito.admin_delete_user(
    	UserPoolId=USER_POOL_ID, Username=username)
    return deleteUserResponse


def addingOrganizationToDatabase(validRequest, generatedOrganizationId):
	ORGANIZATIONJSON = {}
	# databaseConnection = db.getDBConnection()
	createdTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	adminUserId = db.fetch_where_and(
		USER_TABLE, [{"user_name": validRequest['userName']}])[0]['user_id']
	print("adminUser id = ", adminUserId)
	lastAdminId = db.fetch_last_one(USER_TABLE)['admin_id']
	print("last admin id ", lastAdminId)
	userDetails = db.fetch_where_and(
		USER_TABLE, [{'user_name': validRequest['userId']}])[0]
	print("creator details = ", userDetails)
	adminId = userDetails['admin_id']
	print("admin id = ", adminId)
	ORGANIZATIONJSON['organization_name'] = validRequest['organizationName']
	# ORGANIZATIONJSON['admin_id'] = validRequest['userName']
	ORGANIZATIONJSON['admin_id'] = adminUserId
	ORGANIZATIONJSON['address'] = validRequest['organizationAddress']
	ORGANIZATIONJSON['contact_person'] = validRequest['organizationContactPerson']
	ORGANIZATIONJSON['contact_number'] = validRequest['organizationContactMobile']
	ORGANIZATIONJSON['contact_email'] = validRequest['organizationContactEmail']
	ORGANIZATIONJSON['website'] = validRequest['organizationWebsite']
	ORGANIZATIONJSON['created_at'] = createdTime
	ORGANIZATIONJSON['last_updated_at'] = createdTime
	ORGANIZATIONJSON['expire_at'] = validRequest['expireDate']
	# ORGANIZATIONJSON['first_name'] = validRequest['firstName']
	# ORGANIZATIONJSON['last_name'] = validRequest['lastName']
	# if(validRequest['status'] == "True"):
	# 	validRequest['status'] = True
	# else:
	# 	validRequest['status'] = False
	ORGANIZATIONJSON['is_active'] = validRequest['status']
	ORGANIZATIONJSON['created_by'] = adminId
	ORGANIZATIONJSON['organization_id'] = generatedOrganizationId
	ORGANIZATIONJSON['_id'] = generatedOrganizationId
	print("Inserting Value = ", ORGANIZATIONJSON)
	lastUploadedData = db.insert_data_one(ORGANIZATION_TABLE, ORGANIZATIONJSON)
	# newCategoryId = db.fetch_next_id(CAT_MAT, CAT_ID)
	# categoryList = []
	# categoryName = ["Introductory", "Personal",
 #                "Technical", "Behavioural", "Aptitude"]
	# for i in range(len(categoryName)):
	# 	categoryNew = {}
	# 	categoryNew['_id'] = newCategoryId + i
	# 	categoryNew['category_id'] = newCategoryId + i
	# 	categoryNew['category_name'] = categoryName[i]
	# 	categoryNew['organization_id'] = generatedOrganizationId
	# 	categoryNew['created_at'] = createdTime
	# 	categoryList.append(categoryNew)
	# print("Data to be inserted in category table = ", categoryList)
	# catRes = db.insert_data_many(CAT_MAT, categoryList)
	# print("Insert Categoty response = ", catRes)

	print("Last inserted data = ", lastUploadedData)
	return lastUploadedData


def updateOrganizationDetails(validRequest):
	print("updating organization  details")
	print("data to be updated = ", validRequest)
	ORGANIZATIONJSON = {}
	organizationDetailsList = db.fetch_where_and(
		ORGANIZATION_TABLE, [{'organization_id': validRequest['organizationId']}])
	print("========== organization details =========\n ", organizationDetailsList)
	if(len(organizationDetailsList) <= 0):
		print("No organization found")
		response = 402
		return response
	else:
		print("updating organization details in database")
		try:
			organizationDetails = organizationDetailsList[0]
			updatedTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
			ORGANIZATIONJSON['created_by'] = organizationDetails['created_by']
			ORGANIZATIONJSON['organization_id'] = organizationDetails['organization_id']
			ORGANIZATIONJSON['_id'] = organizationDetails['organization_id']
			ORGANIZATIONJSON['created_at'] = organizationDetails['created_at']
			ORGANIZATIONJSON['admin_id'] = organizationDetails['admin_id']
			#DATA GOING TO CHANGE
			ORGANIZATIONJSON['last_updated_at'] = updatedTime
			ORGANIZATIONJSON['organization_name'] = validRequest['organizationName']
			ORGANIZATIONJSON['address'] = validRequest['organizationAddress']
			ORGANIZATIONJSON['contact_person'] = validRequest['organizationContactPerson']
			ORGANIZATIONJSON['contact_number'] = validRequest['organizationContactMobile']
			ORGANIZATIONJSON['contact_email'] = validRequest['organizationContactEmail']
			ORGANIZATIONJSON['website'] = validRequest['organizationWebsite']
			ORGANIZATIONJSON['expire_at'] = validRequest['expireDate']
			ORGANIZATIONJSON['is_active'] = validRequest['status']
			# ORGANIZATIONJSON['first_name'] = validRequest['firstName']
			# ORGANIZATIONJSON['last_name'] = validRequest['lastName']
			print("deleting data in database")
			deleteResponse = db.delete_where(
				ORGANIZATION_TABLE, {"organization_id": validRequest['organizationId']})
			print("deleted response = ", deleteResponse)
			lastUploadedData = db.insert_data_one(ORGANIZATION_TABLE, ORGANIZATIONJSON)
			print("Last inserted data = ", lastUploadedData)
		except Exception as e:
			print("Exception = ", e)
		return lastUploadedData


def lambda_handler(event, context):
	print("event body", event['body'])
	proxyResponse = {}
	response = {}
	proxyResponse['headers'] = {"Access-Control-Allow-Methods": "*",
                             "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}
	validRequest = validateRequest(event)
	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
		return proxyResponse
	else:
		'''
		BUSINESS LOGIC STARTS HERE
		'''
		print("Validated request = ", validRequest)
		#Fetching last organization id

		try:

			if 'organizationId' in validRequest:
				print("Inside organization update")
				updatedDataResponse = updateOrganizationDetails(validRequest)
				print("updated response from the db = ", updatedDataResponse)
				if(updatedDataResponse == 402):
					print("Organization =not= updated successfully")
					proxyResponse['statusCode'] = 402
					proxyResponse['error'] = "Specified organization not found"
					return proxyResponse
				else:
					print("Organization  updated successfully")
					proxyResponse['statusCode'] = 200
					proxyResponse['body'] = "Specified organization updated successfully"
					return proxyResponse
			else:
				if 'userName' not in validRequest and 'password' not in validRequest and 'firstName' not in validRequest and 'lastName' not in validRequest:
					print(MISSING_ERROR_MSG)
					response = {"error": MISSING_ERROR_MSG, "errorCode": 402}
					return response
			print("Adding user to the cognito pool and updating the database")
			organizationCount = db.fetch_count(ORGANIZATION_TABLE)
			if(organizationCount == 0):
				generatedOrganizationId = 1
			else:
				generatedOrganizationId = db.fetch_next_id(
					ORGANIZATION_TABLE, 'organization_id')
				# generatedOrganizationId = previousOrganizationId + 1
			event['body'] = {"username": validRequest['userName'],
                            "password": validRequest['password'],
                            "typeOfUser": RECRUITER,
                            "organizationId": generatedOrganizationId,
                            "firstName": validRequest['firstName'],
                            "lastName": validRequest['lastName']
                    }
			#Invoking ADDUSER lambda to create new user
			createUserResponse = creatingNewUserForOrganization(event)
			print("Created user response from lambda ", createUserResponse)
			#Decoding response from lambda
			decodedCreateUserResponse = json.loads(
				createUserResponse['Payload'].read().decode("utf-8"))
			print("decoded Created user response from lambda", decodedCreateUserResponse)
			if (decodedCreateUserResponse['statusCode'] != 200):
				print("error", decodedCreateUserResponse['error'])
				proxyResponse['error'] = decodedCreateUserResponse['error']
				proxyResponse['statusCode'] = 402
				return proxyResponse
			print("User Successfully created in cognito")
			updatingOrganizationResponse = addingOrganizationToDatabase(
				validRequest, generatedOrganizationId)
			if(updatingOrganizationResponse == 401):
				deleteUserResponse = deleteUser(validRequest['userName'])
				print("User delted response = ", deleteUserResponse)
				reponse = "organization creation failed"
				proxyResponse['statusCode'] = 400
				proxyResponse['error'] = reponse
				return proxyResponse
			response = "organization created Successfully"
		except Exception as e:
			# deleteUserResponse =  deleteUser(validRequest['userName'])
			print("error", e)
			proxyResponse['error'] = e
			proxyResponse['statusCode'] = 402
			return proxyResponse
		response = "Organization created successfully"
		'''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''
		proxyResponse['statusCode'] = 200
		proxyResponse['body'] = json.dumps(response)
	print(proxyResponse)
	return proxyResponse
