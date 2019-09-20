import datetime
import WOHeader
from os import environ
import db_utility
import json
'''
@Author: Shameer
Date of creation: 2018:12:07 19:03:01
Purpose of the micro service: Create a new question for an organisation
'''

'''
ANY TODO

'''

# IMPORT MODULES

# CONSTANTS
MISSING_ERROR_MSG = "Missing required parameter in the request"
UNAUTHENTICATION_ERROR_MSG = "Unauthenticated access. Please give the valid token"
MISSING_LOGIC_MSG = "Missing required logic in request"

# TEST EVENT
testEvent = {"body": {"questionSetId": 2, "questionSetName": "Sample question set3",
                                          "questionList": [{"question_id": 1, "sort_order": 1}, {"question_id": 2, "sort_order": 2},
                                                           {"question_id": 3, "sort_order": 3}, {"question_id": 4, "sort_order": 4}],
                                          "isSampleSet": True, "duration": 10, "expireAt": "22/12/2018",
                                          "isPartialCompleteAllowed": True, "isRandomOrder": True, "isActive": True,
                                          "testMode": 1, "userId": "recruiter@workonic.com"}}

requiredParams = ['questionSetName', 'questionList', 'isSampleSet', 'duration',
                  'isPartialCompleteAllowed', 'isRandomOrder', 'isActive']


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
        if(requestBody['authenticationCode'] != "200"):
            headerValidation = False
    else:
        requestBody = request['body']

    '''
	VALIDATE CANDIDATE TOKEN
	'''
    if('candidateToken' in requestBody):
        if(not db_utility.is_exist("test", {"token": requestBody["candidateToken"], "is_active": True})):
            headerValidation = False

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
    if('error' not in response):
        userInfo = fetch_user_info(requestBody)
        requestBody['userGroupId'] = userInfo['user_group_id']
        requestBody["userId"] = userInfo["user_id"]
        if(not userInfo["is_active"]):
            print(MISSING_LOGIC_MSG)
            print("User permission restricted")
            response = {"error": MISSING_LOGIC_MSG, "errorCode": 402}
        elif(userInfo['user_group_id'] == 2):
            requestBody["organizationId"] = userInfo["organization_id"]
            if(not fetch_organisation_status(requestBody["organizationId"])):
                print(MISSING_LOGIC_MSG)
                print("Organisation permission restricted")
                response = {"error": MISSING_LOGIC_MSG, "errorCode": 402}
            elif('questionSetId' in requestBody and db_utility.is_exist("question_set", {"question_set_id": requestBody['questionSetId'], "is_question_bank": True})):
                print(MISSING_LOGIC_MSG)
                print("Question bank permission restricted")
                response = {"error": MISSING_LOGIC_MSG, "errorCode": 402}
        elif(userInfo['user_group_id'] == 1):
            if('questionSetId' in requestBody and db_utility.is_exist("question_set", {"question_set_id": requestBody['questionSetId'], "is_question_bank": False})):
                print(MISSING_LOGIC_MSG)
                print("Question set permission restricted")
                response = {"error": MISSING_LOGIC_MSG, "errorCode": 402}

    if('error' not in response):
        response = requestBody
    return response


def fetch_user_info(request):
    data = db_utility.fetch_where(
        "user_master", {"user_name": request["userId"]})
    return data[0]


def fetch_organisation_status(organizationId):
    data = db_utility.fetch_where("organization_details", {
        "organization_id": organizationId})[0]
    return data["is_active"]


def lambda_handler(event, context):
    proxyResponse = {}
    response = {}
    proxyResponse['headers'] = {"Access-Control-Allow-Methods": "*",
                                "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}

    validRequest = validateRequest(event)
    print(validRequest)
    if('error' in validRequest):
        proxyResponse['statusCode'] = validRequest['errorCode']
        proxyResponse['error'] = validRequest['error']
    else:
        '''
        BUSINESS LOGIC STARTS HERE
        '''
        if('sampleQuestionSetId' in validRequest):
            sampleQuestionSetId = validRequest['sampleQuestionSetId']
        if('expireAt' in validRequest):
            expireAt = validRequest['expireAt']
        if('organizationId' in validRequest):
            organizationId = validRequest['organizationId']

        isActive = validRequest['isActive']
        questionSetName = validRequest['questionSetName']
        questionList = validRequest['questionList']
        isSampleSet = validRequest['isSampleSet']
        duration = validRequest['duration']
        isPartialCompleteAllowed = validRequest['isPartialCompleteAllowed']
        isRandomOrder = validRequest['isRandomOrder']
        createdBy = validRequest['userId']
        currentTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        param = {}

        if((validRequest['userGroupId']) == 1):
            if('questionSetId' in validRequest):
                param['question_set_name'] = questionSetName
                param['question_list'] = questionList
                param['is_sample_set'] = isSampleSet
                param['duration'] = duration
                param['is_active'] = isActive
                param['is_partial_complete_allowed'] = isPartialCompleteAllowed
                param['last_updated_at'] = currentTime
                param['is_random_order'] = isRandomOrder
                # param['created_by'] = createdBy

                print("Updating question bank")
                questionSetId = validRequest['questionSetId']
                if('expireAt' in validRequest):
                    param['expire_at'] = expireAt
                if('sampleQuestionSetId' in validRequest):
                    param['sample_question_set_id'] = sampleQuestionSetId

                print(param)
                data = db_utility.update_data_one(
                    "question_set", {"question_set_id": questionSetId}, param)
                response["questionSetId"] = questionSetId
            else:
                questionSetId = db_utility.fetch_next_id(
                    "question_set", "question_set_id")

                param['_id'] = questionSetId
                param['question_set_id'] = questionSetId
                param['question_set_name'] = questionSetName
                param['question_list'] = questionList
                param['is_sample_set'] = isSampleSet
                param['is_question_bank'] = True
                param['duration'] = duration
                param['is_active'] = isActive
                param['is_partial_complete_allowed'] = isPartialCompleteAllowed
                param['last_updated_at'] = currentTime
                param['is_random_order'] = isRandomOrder
                param['created_at'] = currentTime
                param['created_by'] = createdBy
                param['is_show'] = True

                print("Creating question bank")

                if('expireAt' in validRequest):
                    param['expire_at'] = expireAt
                if('sampleQuestionSetId' in validRequest):
                    param['sample_question_set_id'] = sampleQuestionSetId

                print(param)
                data = db_utility.insert_data_one("question_set", param)
                response["questionSetId"] = questionSetId
        else:
            if('questionSetId' in validRequest):
                questionSetId = validRequest['questionSetId']
                print("Updating question set")
                param['question_set_name'] = questionSetName
                param['question_list'] = questionList
                param['is_sample_set'] = isSampleSet
                param['duration'] = duration
                param['is_active'] = isActive
                param['is_partial_complete_allowed'] = isPartialCompleteAllowed
                param['last_updated_at'] = currentTime
                param['is_random_order'] = isRandomOrder
                # param['created_by'] = createdBy

                if('organizationId' in validRequest):
                    param['organization_id'] = organizationId
                if('expireAt' in validRequest):
                    param['expire_at'] = expireAt
                if('sampleQuestionSetId' in validRequest):
                    param['sample_question_set_id'] = sampleQuestionSetId

                print(param)
                data = db_utility.update_data_one(
                    "question_set", {"question_set_id": questionSetId}, param)
                response["questionSetId"] = questionSetId

            else:
                print("Creating question set")
                questionSetId = db_utility.fetch_next_id(
                    "question_set", "question_set_id")
                param['_id'] = questionSetId
                param['question_set_id'] = questionSetId
                param['question_set_name'] = questionSetName
                param['question_list'] = questionList
                param['is_sample_set'] = isSampleSet
                param['is_question_bank'] = False
                param['duration'] = duration
                param['is_active'] = isActive
                param['is_partial_complete_allowed'] = isPartialCompleteAllowed
                param['last_updated_at'] = currentTime
                param['is_random_order'] = isRandomOrder
                param['created_at'] = currentTime
                param['created_by'] = createdBy
                param['is_show'] = True

                if('organizationId' in validRequest):
                    param['organization_id'] = organizationId
                if('expireAt' in validRequest):
                    param['expire_at'] = expireAt
                if('sampleQuestionSetId' in validRequest):
                    param['sample_question_set_id'] = sampleQuestionSetId

                print(param)
                data = db_utility.insert_data_one("question_set", param)
                response["questionSetId"] = questionSetId

        '''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''
        proxyResponse['statusCode'] = 200
        proxyResponse['body'] = json.dumps(response)
    print(proxyResponse)
    return proxyResponse


# lambda_handler(testEvent, 100)

