import boto3
import json
import os
import datetime
import lambda_simulator
import sumo_query_function

s3 = boto3.resource('s3')
#lambda_client = boto3.client('lambda')
# DONT FORGET TO SET THE EV LAMBDA_FUNC_NAME to point to the function to run a Sumo query, for example Dev_BI_Sumo_Query
lambda_function_name = os.environ.get('LAMBDA_FUNC_NAME')

def launch_lambda(name, creds, query, streams):
    print("Launching Sumo BI Query: {}".format(query))
    lambda_client = lambda_simulator.LambdaClient(sumo_query_function.lambda_handler,'sample_query')
    resp = lambda_client.invoke(FunctionName=lambda_function_name,
                                InvocationType='Event',
                                Payload=json.dumps({'query': query, 'name': name, 'creds': creds, 'streams':streams}))
    print("Got response: {}".format(resp))
    
def load_queries(bucket, json_config_file_name):
    #1 - get file from s3. File should be a JSON file similar to test.json
    #2 - bucket name should be env vars passed to the function
    print("Orchestrator reading from {}".format(json_config_file_name))
    obj = s3.Object(bucket, json_config_file_name)
    data = json.loads(obj.get()['Body'].read().decode('utf-8'))
    #print(data)
    # run all BI
    if ('queries' in data):
        for query in data.get('queries'):
            print("Got SUMO BI Query: {}".format(query['name']))
            n = query['name']
            c = query['creds']
            q = query['query']
            s = query['streams']
            launch_lambda(n, c, q, s)

    if ('others' in data):    
        for other in data.get('others',None):
            print("Lauching other function: {}".format(other['name']))
            resp = lambda_client.invoke(FunctionName=other['name'],
                                    InvocationType='Event',
                                    Payload=json.dumps(other))
            print(resp)

def lambda_handler(req, context):
    print("Invoke ARN: {} ".format(context.invoked_function_arn))
    trigger = req.get("resources",None)
    ruleName = trigger[0].split('rule/')[1] if (trigger is not None) else 'JSON_CONFIG_FILE_NAME'
    try:
        st=datetime.datetime.now()
        b = os.environ.get('CONFIG_BUCKET')
        # Get the path to the config file
        json_config_file_name = os.environ.get(ruleName)
        print("Querying: {}".format(json_config_file_name))
        load_queries(b, json_config_file_name)
    except Exception as e:
        print(e)

