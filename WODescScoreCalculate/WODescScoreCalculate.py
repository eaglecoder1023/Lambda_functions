import db_utility as db
import math
import boto3
import json
import time
import threading
import datetime
from os import environ
from botocore.config import Config
#constants
TEST_RES = "test_response"
TEST = "test"
REGION = environ['Region']
config = Config(
    retries=dict(
        max_attempts=1
    ), read_timeout=900
)
requiredParams = ['candidateToken']
#Checking Required Parameters


def checkAllRequiredValuesPresent(request):
    for param in requiredParams:
        if(param not in request):
            print("The value "+param+" missing")
            return False
    return True

#Function Calling External Lambdas


def lambdaaCallFunctionforTranscribe(event):
    function_name = "WO-"+environ['stage']+"-TranscribeVideo"
    print("called function name = ", function_name)
    newEvent = {}
    newEvent['responseId'] = event['response_id']
    newEvent['testId'] = event['test_id']
    newEvent['questionId'] = event['question_id']
    newEvent['videoUrl'] = environ['videourl']+event['video_url']
    print(newEvent)
    lambdaCall = boto3.client('lambda', region_name=REGION, config=config)
    print("=============Calling lambda==============")
    lambdaResponse = lambdaCall.invoke(FunctionName=function_name,
                                       InvocationType='RequestResponse', LogType='Tail', Payload=json.dumps(newEvent))
    print("============= lambda Called and Response ==============")
    print("response = ", lambdaResponse)


def lambdaaCallFunctionforRekognition(event):
    function_name = "WO-"+environ['stage']+"-LabelDetection"
    print("called function name = ", function_name)
    newEvent = {}
    newEvent['responseId'] = event['response_id']
    newEvent['testId'] = event['test_id']
    newEvent['questionId'] = event['question_id']
    newEvent['videoUrl'] = environ['videourl']+event['video_url']
    print(newEvent)
    lambdaCall = boto3.client('lambda', region_name=REGION, config=config)
    print("=============Calling lambda==============")
    lambdaResponse = lambdaCall.invoke(FunctionName=function_name,
                                       InvocationType='RequestResponse', LogType='Tail', Payload=json.dumps(newEvent))
    print("============= lambda Called and Response ==============")
    print("response = ", lambdaResponse)


#CALLING LAMBDA FUNCTIONS
def callingLambdaFunctionsInThread(response):
    thread = {}
    for i in response:
        thread[i] = threading.Thread(
            target=lambdaaCallFunctionforTranscribe, args=(response[i],))
        thread[i+i] = threading.Thread(
            target=lambdaaCallFunctionforRekognition, args=(response[i],))
        thread[i].start()
        time.sleep(0.1)
        thread[i+i].start()
        time.sleep(0.2)
    return 200

#GETTING URLS FROM TABLE


def getUrlsFromTable(testId):
    questionListWithUrl = db.fetch_where_and(TEST_RES, [{"test_id": testId}])
    if(len(questionListWithUrl) == 0):
        return 402
    urls = {}
    urlLength = False
    for i in questionListWithUrl:
        if "video_url" in i:
            urlLength = True
            urls[i['response_id']] = {"response_id": i['response_id'], "test_id": testId,
                                      "question_id": i['question_id'], "video_url": i['video_url']}
    if(urlLength):
        return urls
    else:
        return 403


#Checking candidate Token
def CandidateTokenCheck(tokenId):
    testDetails = db.fetch_where_and(TEST, [{"token": tokenId}])
    print("Test details = ", testDetails)
    if(len(testDetails) == 0):
        return 402
    else:
        return testDetails[0]['test_id']

#LambdaHandler


def lambda_handler(event, context):
    print("EVNT = ", event)
    if 'body' in event:
        oldEvent = event
        event = oldEvent['body']
    proxyresponse = {}
    proxyresponse['headers'] = {"Access-Control-Allow-Methods": "*",
                                "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Origin": "*"}
    if(not checkAllRequiredValuesPresent(event)):
        proxyresponse['error'] = "Missing parameters"
        proxyresponse['statusCode'] = 402
        return proxyresponse

    testId = CandidateTokenCheck(event['candidateToken'])

    #Candidate Checking
    if(testId == 402):
        proxyresponse['error'] = "No Candiate Found"
        proxyresponse['statusCode'] = 402
        return proxyresponse

    response = getUrlsFromTable(testId)
    #Questions Checking
    if(response == 402):
        proxyresponse['error'] = "No question Found"
        proxyresponse['statusCode'] = 402
        return proxyresponse
    elif(response == 403):
        proxyresponse['error'] = "No descriptive question Found"
        proxyresponse['statusCode'] = 402
        return proxyresponse
    callLambda = callingLambdaFunctionsInThread(response)

    #Thread Calling check
    if(callLambda == 200):
        proxyresponse['body'] = "Score calculating process begun"
        proxyresponse['statusCode'] = 200
        return proxyresponse
    else:
        proxyresponse['error'] = "Error in process"
        proxyresponse['statusCode'] = 402
        return proxyresponse
