import string
import random
import datetime
import pymongo
import boto3
import db_utility
import WOHeader
from os import environ
import json
import pandas as pd
import io
# from StringIO import StringIO
from io import StringIO

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

# testEvent= {'body':{'first_name':'Sha','userId':'recruiter@workonic.com','email':'ssaleem@whirldatascience.com','question_set_id':18}}
requiredParams = ["question_set_id"]
# requiredParamsInCSV=['firstName','eMail']
# df=pd.read_csv("CreateTest.csv")
# testEvent={'body':{'userId':'recruiter@workonic.com','question_set_id':2,'csv':df}}
def checkAllRequiredValuesPresent(request):
    error=False
    for i in range(request['csv'].shape[0]):
        # print(request['csv'].loc[i,'firstName'])
        # print(pd.isnull(request['csv'].loc[i,'firstName']))
        if pd.isnull(request['csv'].loc[i,'firstName']) or pd.isnull(request['csv'].loc[i,'email']):
            print("The Required Value is missing at position "+str(i+1))
            error=True
    if (error):
        return False
    else:
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
    print(event['body'])
    Bucket=event['body']['Bucket']
    # Bucket="workonic-media-files"
    # key="mainCSV/6_Sample.csv"
    key=event['body']['Key']
    print(key)
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=Bucket, Key=key)
    emailcontent = obj['Body'].read().decode('utf-8')
    print("YES")
    TESTDATA = StringIO(emailcontent)
    df = pd.read_csv(TESTDATA, sep=",")
    print(df)
    event['body']['csv']=df

    # for bucket in s3.buckets.all():
    #     print(bucket.name)
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
        userDetail = db_utility.fetch_where("user_master", {"user_name": userName})[0]
        # print(userDetail)
        csvFile=validRequest['csv']
        insertionFailed=[]
        for i in range(csvFile.shape[0]):
            # print(csvFile.loc[i])
            candidate_param = {}
            test_param = {}
            tracker_param = {}
            invitation_param = {}
            param = {}
            firstName=csvFile.loc[i,'firstName']
            email=csvFile.loc[i,'email']
            print(email)
            candidate_param['candidate_id'] = db_utility.fetch_next_id("candidate", "candidate_id")
            candidate_param["_id"] = candidate_param["candidate_id"]
            candidate_param['first_name'] = firstName
            if (not pd.isnull(csvFile.loc[i,'lastName'])):
                lastName=csvFile.loc[i,'lastName']
                candidate_param['last_name'] = lastName
            candidate_param['email'] = email
            candidate_param['is_active'] = True
            candidate_param['created_at'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            candidate_param['organization_id'] = userDetail['organization_id']
            candidate_param['created_by'] = userDetail['user_id']

            questionSetDetail = db_utility.fetch_where("question_set", {"question_set_id": validRequest['question_set_id']})[0]
            
            test_param['test_id'] = db_utility.fetch_next_id("test", "test_id")
            test_param["_id"] = test_param["test_id"]
            test_param['candidate_id'] = candidate_param["candidate_id"]
            test_param['created_at'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            test_param['question_set_id'] = validRequest['question_set_id']
            test_param['is_active'] = True
            test_param['created_at'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
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
            tracker_param['tracker_id'] = db_utility.fetch_next_id("log_tracker", "tracker_id")
            tracker_param["_id"] = tracker_param['tracker_id']
            tracker_param['test_id'] = test_param['test_id']
            tracker_param['activity_type_id'] = "000"
            tracker_param['activity_time'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            candidate_data = db_utility.insert_data_one("candidate", candidate_param)
            test_data = db_utility.insert_data_one("test", test_param)
            tracker_data = db_utility.insert_data_one("log_tracker", tracker_param)

            if candidate_data == "200" and tracker_data == "200" and test_data=="200":
                print("Data Inserted")
                param = tracker_param
                orgDetail = db_utility.fetch_where("organization_details", {"organization_id": userDetail['organization_id']})[0]

                organisation_name = orgDetail['organization_name']
                test_name = questionSetDetail['question_set_name']
                first_name = firstName
                recruiter_name = orgDetail['organization_name']
                recruiter_phone = orgDetail['contact_number']
                test_url = environ.get('TESTURL')+'/#/token/'+token
                # test_url = 'localhost:4200/token/'+token
                recruiter_email = orgDetail['contact_email']
                test_duration = questionSetDetail['duration']
                test_expire = questionSetDetail['expire_at']

                inviteParam = {'organisation_name': organisation_name, 'test_name': test_name, 'first_name': first_name, 'recruiter_name': recruiter_name, 'test_url': test_url,
                            'recruiter_phone': recruiter_phone, 'recruiter_email': recruiter_email, 'test_duration': test_duration, 'test_expire': test_expire}

                request = {"to": [email],"parameters": inviteParam, 'templateName': 'test_invite', 'candidateToken':token}
                client = boto3.client('lambda', region_name=environ['Region'])
                response = client.invoke(
                    FunctionName='WO-'+environ['stage']+'-SendEmail',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({'body':request})
                )
                # response=json.loads(response['Payload'].read().decode("utf-8"))
                # print(response)
                response = "200"
                if response == "200":
                    print("Test Invitation Sent")
                    invitation_param['tracker_id'] = db_utility.fetch_next_id("log_tracker", "tracker_id")
                    invitation_param["_id"] = invitation_param['tracker_id']
                    invitation_param['test_id'] = test_param['test_id']
                    invitation_param['activity_type_id'] = "001"
                    invitation_param['activity_time'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    invitation_data = db_utility.insert_data_one("log_tracker", invitation_param)
                else:
                    param['statusCode'] = 400
                    param['Error'] = DATABASE_CONNECTION_ERROR
                    param['erroMessage']="Sending Inivitation Failed"
                    invitation_data="0"
                if invitation_data == "200":
                    print("Invitation Data Inserted")
                    param['statusCode']=200
                    param['Message']="All User Inserted"
                else:
                    param['statusCode'] = 400
                    param['Error'] = DATABASE_CONNECTION_ERROR
                    insertionFailed.append(i)
                    param["insertionFailedFor"]=insertionFailed
            else:
                param['statusCode'] = 400
                param['Error'] = DATABASE_CONNECTION_ERROR
                insertionFailed.append(i)
                param["insertionFailedFor"]=insertionFailed
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

# lambda_handler(testEvent,100)

