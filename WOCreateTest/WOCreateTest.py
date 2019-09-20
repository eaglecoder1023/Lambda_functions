import string
import random
import datetime
import pymongo
import boto3
import db_utility
import WOHeader
from os import environ
import json
'''
@Author: <SaqibKhaleel>
Date of creation: 2018:12:08 15:45:00
Purpose of the micro service: <DESCRIPTION BY AUTHOR>
'''

'''
ANY TODO

'''

# IMPORT MODULES

# CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
DATABASE_CONNECTION_ERROR = "Failed to insert in the Database"

requiredParams = ["first_name", "email", "question_set_id"]


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
        if(requestBody['authenticationCode'] != "200"):
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
        response = {"error": UNAUTHENTICATION_ERROR_MSG, "errorCode": 404}
    elif(not checkAllRequiredValuesPresent(requestBody)):
        print(MISSING_ERROR_MSG)
        response = {"error": MISSING_ERROR_MSG, "errorCode": 402}
    '''
	BUSINESS LOGIC VALIDATION HERE
	'''
    if "error" not in response:
        response = requestBody
    return response


def validateCandidate(requestBody):
    return 0


def lambda_handler(event, context):
    proxyResponse = {}
    response = {}
    proxyResponse['headers'] = {"Access-Control-Allow-Methods": "*",
                                "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}

    validRequest = validateRequest(event)
    if('error' in validRequest):
        proxyResponse['statusCode'] = validRequest['errorCode']
        proxyResponse['error'] = validRequest['error']
    else:
        '''
        BUSINESS LOGIC STARTS HERE
        '''
        userName = validRequest['userId']
        userDetail = db_utility.fetch_where(
            "user_master", {"user_name": userName})[0]
        print(userDetail)
        candidate_param = {}
        test_param = {}
        tracker_param = {}
        invitation_param = {}
        param = {}

        # for i in requiredParams:
        # 	candidate_param[i]=validRequest[i]

        candidate_param['candidate_id'] = db_utility.fetch_next_id(
            "candidate", "candidate_id")
        candidate_param["_id"] = candidate_param["candidate_id"]
        candidate_param['first_name'] = validRequest['first_name']
        if 'last_name' in validRequest:
            candidate_param['last_name'] = validRequest['last_name']
        if 'mobile_number' in validRequest:
            candidate_param['mobile_number'] = validRequest['mobile_number']
        candidate_param['email'] = validRequest['email']
        candidate_param['is_active'] = True
        candidate_param['created_at'] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S")
        candidate_param['organization_id'] = userDetail['organization_id']
        candidate_param['created_by'] = userDetail['user_id']

        questionSetDetail = db_utility.fetch_where("question_set", {"question_set_id": validRequest['question_set_id']})[0]
        # print(questionSetDetail)
        test_param['test_id'] = db_utility.fetch_next_id("test", "test_id")
        test_param["_id"] = test_param["test_id"]
        test_param['candidate_id'] = candidate_param["candidate_id"]
        test_param['created_at'] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S")
        test_param['question_set_id'] = validRequest['question_set_id']
        test_param['is_active'] = True
        test_param['created_at'] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S")
        test_param['organization_id'] = userDetail['organization_id']
        test_param['created_by'] = userDetail['user_id']
        test_param['expire_at']=questionSetDetail['expire_at']
        while True:
            token = ''.join(random.choice(string.ascii_lowercase)
                            for i in range(10))
            # print(token)
            tokenValidation = db_utility.is_exist("test", {"token": token})
            if (not tokenValidation):
                test_param['token'] = token
                break
            else:
                continue

        tracker_param = {}
        tracker_param['tracker_id'] = db_utility.fetch_next_id(
            "log_tracker", "tracker_id")
        tracker_param["_id"] = tracker_param['tracker_id']
        tracker_param['test_id'] = test_param['test_id']
        tracker_param['activity_type_id'] = "000"
        tracker_param['activity_time'] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S")

        candidate_data = db_utility.insert_data_one(
            "candidate", candidate_param)
        test_data = db_utility.insert_data_one("test", test_param)
        tracker_data = db_utility.insert_data_one("log_tracker", tracker_param)

        if candidate_data == "200" and tracker_data == "200" and test_data=="200":
            print("Data Inserted")
            param = tracker_param
            orgDetail = db_utility.fetch_where(
                "organization_details", {"organization_id": userDetail['organization_id']})[0]

            organisation_name = orgDetail['organization_name']
            test_name = questionSetDetail['question_set_name']
            first_name = validRequest['first_name']
            recruiter_name = orgDetail['organization_name']
            recruiter_phone = orgDetail['contact_number']
            test_url = environ.get('TESTURL')+'/#/token/'+token
            recruiter_email = orgDetail['contact_email']
            test_duration = questionSetDetail['duration']
            test_expire = questionSetDetail['expire_at']

            inviteParam = {'organisation_name': organisation_name, 'test_name': test_name, 'first_name': first_name, 'recruiter_name': recruiter_name, 'test_url': test_url,
                        'recruiter_phone': recruiter_phone, 'recruiter_email': recruiter_email, 'test_duration': test_duration, 'test_expire': test_expire}

            request = {"to": [validRequest['email']],
                    "parameters": inviteParam, 'templateName': 'test_invite', 'candidateToken':token}

            client = boto3.client('lambda', region_name=environ['Region'])
            response = client.invoke(
                FunctionName='WO-'+environ['stage']+'-SendEmail',
                InvocationType='RequestResponse',
                Payload=json.dumps({'body':request})
            )

            response = "200"
            if response == "200":
                print("Test Invitation Sent")
                invitation_param['tracker_id'] = db_utility.fetch_next_id(
                    "log_tracker", "tracker_id")
                invitation_param["_id"] = invitation_param['tracker_id']
                invitation_param['test_id'] = test_param['test_id']
                invitation_param['activity_type_id'] = "001"
                invitation_param['activity_time'] = datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S")
                invitation_data = db_utility.insert_data_one(
                    "log_tracker", invitation_param)
            else:
                param['statusCode'] = 400
                param['Error'] = DATABASE_CONNECTION_ERROR
                param['erroMessage']="Sending Inivitation Failed"
                invitation_data="0"
            if invitation_data == "200":
                print("Invitation Data Inserted")
                param = invitation_param
            else:
                param['statusCode'] = 400
                param['Error'] = DATABASE_CONNECTION_ERROR
        else:
            param['statusCode'] = 400
            param['Error'] = DATABASE_CONNECTION_ERROR
        response = param

    '''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''
    proxyResponse['statusCode'] = 200
    # response={}
    # print(response)
    proxyResponse['body'] = json.dumps(response)
    print(proxyResponse)
    return proxyResponse

# testEvent= {'body':{'first_name':'Sha','userId':'recruiter@workonic.com','email':'ssaleem@whirldatascience.com','question_set_id':18}}
# lambda_handler(testEvent,100)

