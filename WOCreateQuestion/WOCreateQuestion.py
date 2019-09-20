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
testEvent = {"body": {"questionTitle": "Val1",
                      "questionDescription": "Val1", "questionTypeId": 2,
                      "containsMedia": False, "testMode": 1, "userId": "sameer", "duration": 0}}

requiredParams = ['questionTitle',
                  'questionDescription', 'questionTypeId', 'duration']


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
    # if('candidateToken' in requestBody):
    # 	candidateInfo = validateCandidate(requestBody)
    # 	requestBody['candidate'] = candidateInfo

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
        requestBody["userGroupId"] = userInfo["user_group_id"]
        requestBody["userId"] = userInfo["user_id"]
        if(not userInfo["is_active"]):
            print(MISSING_LOGIC_MSG)
            print("User permission restricted")
            response = {"error": MISSING_LOGIC_MSG, "errorCode": 402}
        elif(requestBody['userGroupId'] == 1):
            requestBody["adminId"] = userInfo['admin_id']
        elif(requestBody['userGroupId'] == 2):
            requestBody["organizationId"] = userInfo["organization_id"]
            if(not fetch_organisation_status(requestBody["organizationId"])):
                print(MISSING_LOGIC_MSG)
                print("Organisation permission restricted")
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
                                  "organization_id": organizationId})
    return data[0]["is_active"]


def delete_all(tableName, condition):
    try:
        db = db_utility.getDBConnection()
        collection = db[tableName]
        collection.delete_many(condition)
    except Exception as e:
        print(e)
        return "401"
    else:
        return "200"


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
        questionTitle = validRequest["questionTitle"]
        questionDescription = validRequest["questionDescription"]
        questionTypeId = validRequest["questionTypeId"]
        if not validRequest["imageList"]:
            containsMedia = False
        else:
            containsMedia = True
        createdTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        duration = validRequest["duration"]
        createdBy = validRequest["userId"]
        optionList = validRequest['optionList']
        categoryList = validRequest['categoryList']
        score = validRequest['score']

        if('questionId' not in validRequest):
            questionId = db_utility.fetch_next_id(
                "question_master", "question_id")
            param = {"_id": questionId, "question_id": questionId, "title": questionTitle, "description": questionDescription, "question_type_id": questionTypeId,
                     "contains_media": containsMedia, "score": score, "is_active": True, "last_updated_at": createdTime, "created_at": createdTime, "created_by": createdBy, "duration": duration}
            if(validRequest['userGroupId'] == 1):
                param['admin_id'] = validRequest['adminId']
            if(validRequest['userGroupId'] == 2):
                param['organization_id'] = validRequest["organizationId"]
            if(questionTypeId == 1):
                if('answer_count' in validRequest):
                    param['answer_count'] = validRequest["answer_count"]
            if(containsMedia):
                param['image_list']=validRequest['imageList']
            data = db_utility.insert_data_one("question_master", param)

            response["question_id"] = questionId
            response["responseCode"] = "200"
            response["message"] = "Question created successfully"

        else:
            questionId = validRequest["questionId"]
            param = {"title": questionTitle, "description": questionDescription, "question_type_id": questionTypeId,
                     "contains_media": containsMedia, "score": score, "last_updated_at": createdTime, "created_by": createdBy, "duration": duration}
            if(questionTypeId == 1):
                if('answer_count' in validRequest):
                    param['answer_count'] = validRequest["answer_count"]
            if(containsMedia):
                param['image_list']=validRequest['imageList']
            data = db_utility.update_data_one(
                "question_master", {"question_id": questionId}, param)
            if(data == "200"):
                response["question_id"] = questionId
                response["responseCode"] = "200"
                response["message"] = "Question updated successfully"
            data = delete_all("question_category", {"question_id": questionId})
            data = delete_all("question_tags", {"question_id": questionId})
            data = delete_all("question_mcq", {"question_id": questionId})

        questionCategoryId = db_utility.fetch_next_id(
            "question_category", "question_category_id")
        paramList = []
        for category in categoryList:
            param = {}
            param["_id"] = questionCategoryId
            param["question_category_id"] = questionCategoryId
            param["question_id"] = questionId
            param["category_id"] = category["categoryId"]
            questionCategoryId = questionCategoryId + 1
            paramList.append(param)
        print("Inserting categories")
        data = db_utility.insert_data_many("question_category", paramList)

        if(questionTypeId == 1):
            optionId = db_utility.fetch_next_id("question_mcq", "option_id")
            paramList = []
            for option in optionList:
                param = {}
                param["_id"] = optionId
                param["option_id"] = optionId
                param["question_id"] = questionId
                param["option"] = option["option"]
                param["score"] = option["score"]
                param["is_correct"] = option["isCorrect"]
                optionId = optionId + 1
                paramList.append(param)
            print("Inserting options")
            data = db_utility.insert_data_many("question_mcq", paramList)

        if('tagList' in validRequest):
            # tagList = db_utility.fetch_where("question_tags",{"question_id":questionId})
            for tag in validRequest['tagList']:
                tagInfo = db_utility.fetch_where("tag",{"tag_name":tag['tag_name']})
                if(len(tagInfo)>0):
                    tagId = tagInfo[0]['tag_id']
                else:
                    tagId = db_utility.fetch_next_id("tag", "tag_id")
                    data = db_utility.insert_data_one("tag", {"_id":tagId,"tag_id":tagId,"tag_name":tag['tag_name']})
                questionTagId = db_utility.fetch_next_id("question_tags", "question_tag_id")
                data = db_utility.insert_data_one("question_tags", {"_id":questionTagId,"question_tag_id":questionTagId,"tag_id":tagId,"question_id":questionId})
        '''
		BUSINESS LOGIC ENDS HERE BY RETURNING RESPONSE JSON
		'''
        proxyResponse['statusCode'] = 200
        proxyResponse['body'] = json.dumps(response)
    print(proxyResponse)
    return proxyResponse

# lambda_handler(testEvent,100)

