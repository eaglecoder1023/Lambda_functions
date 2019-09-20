import WOHeader
import db_utility as db
import datetime
from os import environ
import json
import boto3
import pymongo
import time


MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
CLIENT_ID = environ['clientId']
USER_TABLE = 'user_master'
ADMIN = 'admin'
RECRUITER = 'recruiter'
typeOfUsser = None
isActive = True
USER_POOL_ID = environ['userpoolid']
requiredParams = ['username', 'password', "firstName", "lastName"]
USER_GROUP = 'user_group'
ORGNATION_TABLE = "organization_details"

requiredParams = ['username', 'password']


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
	if('candidateToken' not in request['body'] and 'testMode' not in request['body'] and environ.get('isHeaderValidationRequired')):
		requestBody = WOHeader.run(request)
		print("request body", requestBody)
		if(requestBody['authenticationCode'] != '200'):
			headerValidation = False
			print(UNAUTHENTICATION_ERROR_MSG)
			response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
			return response
		print("userId = ", requestBody['userId'])

		# userGroupId = db.fetch_where_and(USER_TABLE, [{'user_name': requestBody['userId']}])[0]['user_group_id']
		# print("user group id =  ", userGroupId)
		# requestBody['userDBid']
		# userGroupName = db.fetch_where_and(USER_GROUP, [{'user_group_id': userGroupId}])[
		#								   0]['user_group_name']
		# print("Creating user group name = ", userGroupName)
		# requestBody['userGroup'] = userGroupName
		# print("user group name = ", userGroupName)
		# requestBody['userGroup'] == userGroupName

		userDetails = db.fetch_where_and(
			USER_TABLE, [{'user_name': requestBody['userId']}])[0]
		print("creator details = ", userDetails)
		userStaus = userDetails['is_active']
		print("user status = ", userStaus)
		if(userStaus == False):
			print(UNAUTHENTICATION_ERROR_MSG)
			response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
			return response
		# userGroupId = /db.fetch_where_and(USER_TABLE, [{'user_name': requestBody['userId']}])[0]['user_group_id']
		userGroupId = userDetails['user_group_id']
		print("userGroup id = ", userGroupId)
		adminId = userDetails['admin_id']
		print("admin id = ", adminId)
		userId = userDetails['user_id']
		requestBody['userDBid'] = userId
		print("userId = ", userId)
		print("user group id =  ", userGroupId)
		userGroupName = db.fetch_where_and(
			USER_GROUP, [{'user_group_id': userGroupId}])[0]['user_group_name']
		print("user group name = ", userGroupName)
		requestBody['userGroup'] = userGroupName

		if userGroupName == RECRUITER:
			requestBody['typeOfUser'] = RECRUITER
			# orgDetails = db.fetch_where_and(USER_TABLE,[{'user_name':requestBody['userId']}])[0]
			orgDetails = db.fetch_where_and(
				ORGNATION_TABLE, [{'organization_id': userDetails['organization_id']}])[0]
			print("recruiter organization details = ", orgDetails)
			if(orgDetails['is_active'] == False):
				response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
				return response
			if(orgDetails['admin_id'] != userDetails['user_id']):
				response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
				return response
			requestBody['organizationId'] = orgDetails['organization_id']
			# requestBody['organizationId'] = db.fetch_where_and(USER_TABLE,[{'user_name':requestBody['userId']}])[0]['organization_id']

		elif userGroupName == ADMIN:
			# This happens when Admin create a new organization
			if 'organizationId' in requestBody:
				requestBody['typeOfUser'] = RECRUITER
			else:
				requestBody['typeOfUser'] = ADMIN
		requestBody = request['body']
	else:
		requestBody = request['body']

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
	response = requestBody
	return response


def creatinUserInCognito(username, password):
	proxyResponse = {}
	try:
		cognito = boto3.client('cognito-idp', region_name=environ['cognitoregion'])
		user_create_response = cognito.sign_up(ClientId=CLIENT_ID, Username=username, Password=password, UserAttributes=[
                    {'Name': 'email', 'Value': username}])
	except Exception as e:
		proxyResponse['error'] = "Error while creating User ,User exists already"
		print(e)
		proxyResponse['statusCode'] = 402
		return proxyResponse
	return user_create_response


def addUserToGroup(username, groupname):
	proxyResponse = {}
	try:
		cognito = boto3.client('cognito-idp', environ['cognitoregion'])
		user_group_add_response = cognito.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    GroupName=groupname
                )
		return user_group_add_response
	except Exception as e:
		proxyResponse['error'] = "Error while adding User to group"
		print(e)
		proxyResponse['statusCode'] = 402
		return proxyResponse


def deleteUser(username):
	cognito = boto3.client('cognito-idp', region_name=environ['cognitoregion'])
	deleteUserResponse = cognito.admin_delete_user(
		UserPoolId=USER_POOL_ID, Username=username)
	return deleteUserResponse


def updatingUserInDatabase(validRequest):
	lastAdminId = db.fetch_last_one(USER_TABLE)['admin_id']
	print("last admin id ", lastAdminId)
	dbInsertDocument = {}
	print("Document to be updated in the table", dbInsertDocument)
	proxyResponse = {}
	database = db.getDBConnection()
	print("Finding last user id...")
	currentUserId = int(db.fetch_next_id(USER_TABLE, "_id"))
	# print("previous user id =  ",previousUser)
	print("Document to be updated in the table before data insert in json = ",
	      dbInsertDocument)
	# previousUserId = previousUser['user_id']
	# currentUserId = previousUserId + 1
	createdTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	if(validRequest['typeOfUser'] == RECRUITER and validRequest['userGroup'] == ADMIN):
		dbInsertDocument['organization_id'] = validRequest['organizationId']
		dbInsertDocument['user_group_id'] = 2
	elif(validRequest['userGroup'] == RECRUITER):
		dbInsertDocument['organization_id'] = validRequest['organizationId']
		dbInsertDocument['user_group_id'] = 2
	else:
		dbInsertDocument['user_group_id'] = 1
	# Greating document to insert in database
	dbInsertDocument['admin_id'] = lastAdminId
	dbInsertDocument["_id"] = currentUserId
	dbInsertDocument['user_id'] = currentUserId
	dbInsertDocument['user_name'] = validRequest['username']
	dbInsertDocument['email'] = validRequest['username']
	dbInsertDocument['created_at'] = createdTime
	dbInsertDocument['last_updated_at'] = createdTime
	dbInsertDocument['is_active'] = isActive
	dbInsertDocument['first_name'] = validRequest['firstName']
	dbInsertDocument['last_name'] = validRequest['lastName']
	dbInsertDocument['created_by'] = validRequest['userDBid']
	print("Document to be updated in the table", dbInsertDocument)
	insertResponse = db.insert_data_one(USER_TABLE, dbInsertDocument)
	print("DataBase inserted response = ", insertResponse,
	      " type = ", type(insertResponse))
	return insertResponse


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

	print("VALIDATED REQUEST = ", validRequest)
	if('error' in validRequest):
		proxyResponse['statusCode'] = validRequest['errorCode']
		proxyResponse['error'] = validRequest['error']
		return proxyResponse
	else:
		# BUSINESS LOGIC STARTS HERE
		try:
			# finding type of user {Admin or Recruiter}
			if (validRequest['typeOfUser'] == ADMIN):
				groupname = ADMIN
			elif(validRequest['typeOfUser'] == RECRUITER):
				groupname = RECRUITER
			print("Addding user in cognito")
			print("valid red", validRequest)
			user_create_response = creatinUserInCognito(
				validRequest['username'], validRequest['password'])
			print("user created response", user_create_response)
			if(user_create_response['ResponseMetadata']['HTTPStatusCode'] == 402):
				print("USER CREATION ERROR")
				proxyResponse['statusCode'] = 402
				proxyResponse['error'] = "Error while creating User ,User exists already"
				return proxyResponse

			print("User created response = ", user_create_response)
			print("Adding user to group")
			user_added_to_group = addUserToGroup(validRequest['username'], groupname)
			user_to_update_in_database = updatingUserInDatabase(validRequest)
			if(user_to_update_in_database != '200'):
				deleteUserResponse = deleteUser(user_create_response['username'])
				proxyResponse['statusCode'] = 402
				proxyResponse['error'] = "Error while updating database"
		except Exception as e:
			proxyResponse['error'] = "Error while creating User ,Error in process"
			print(e)
			proxyResponse['statusCode'] = 402
			return proxyResponse
		print("VALIDATED REQUEST = ", validRequest)
		response['statusCode'] = 200
		response['body'] = 'user created successfully'
		proxyResponse['statusCode'] = 200
		proxyResponse['body'] = json.dumps(response)
		print("Proxy response  =  ", proxyResponse)
	return proxyResponse
