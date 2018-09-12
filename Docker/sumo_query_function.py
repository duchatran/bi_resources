from botocore.vendored import requests
import datetime
import csv
import boto3
import os
from base64 import b64decode
import logging
from sumo import *
import stash
import copy
import lambda_simulator

s3_client = boto3.client('s3')
#lambda_client = boto3.client('lambda')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def export_data(data, headers, query_name, out_bucket):
    file_name = '/tmp/sumo_{}_{}.csv'.format(query_name, datetime.datetime.now().strftime("%Y-%m-%d"))
    with open(file_name, 'w') as f:
        file = csv.DictWriter(f, fieldnames=headers)
        file.writeheader()
        file.writerows(data)

    s3_client.upload_file(file_name, out_bucket, file_name.split('/')[-1])


def lambda_handler(req, context):
    query_name = req['name']
    query = req['query']
    # creds field format is <id,key,region> for the target Sumo account.
    #print(os.environ.get('CREDS_COMBO'))
    mcreds = req['creds']
    streams = req['streams'].split(',')
    timenow = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    
    if (('from' in req) and ('to' in req)):
        from_time  =datetime.datetime.strptime(req['from'],"%Y-%m-%dT%H:%M:%S") 
        to_time  = datetime.datetime.strptime(req['to'],"%Y-%m-%dT%H:%M:%S")
    else:
        to_time = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        from_time = (to_time - datetime.timedelta(days=1))
        req['from'] = from_time.strftime("%Y-%m-%dT%H:%M:%S")
        req['to'] = to_time.strftime("%Y-%m-%dT%H:%M:%S")
    timerange = {'from':from_time,'to':to_time}    
    
    # For first call, we may need to break up into smaller chunks (1-day, or some hourly chunks depending on the input)
    if (not('subcall' in req)):
            daygap = (to_time-from_time).days
            #lambda_client = boto3.client('lambda')
            lambda_client = lambda_simulator.LambdaClient(lambda_handler,'sample_query')
            if (daygap<1):
                # just invoke as is
                new_req = copy.copy(req)
                new_req['subcall'] = 1
                logger.info("Now self-invoke with this payload: {}".format(new_req))        
                lambda_client.invoke(FunctionName=context.function_name, InvocationType='Event',Payload=json.dumps(new_req))
                return
            for i in range(daygap):
                new_req = copy.copy(req)
                new_req['subcall'] = 1
                begin_time = from_time + datetime.timedelta(days = i)
                subquery_count = req.get('subquery_count',1)
                hour_per_query = int(24/subquery_count)
                for h in range(subquery_count):
                    sub_begin_time = begin_time + datetime.timedelta(hours = h*hour_per_query)
                    sub_end_time = begin_time + datetime.timedelta(hours = (h+1)*hour_per_query)
                    new_req['from'] = sub_begin_time.strftime("%Y-%m-%dT%H:%M:%S")
                    new_req['to']= sub_end_time.strftime("%Y-%m-%dT%H:%M:%S")
                    logger.info("Now self-invoke with this payload: {}".format(new_req))        
                    lambda_client.invoke(FunctionName=context.function_name, InvocationType='Event',Payload=json.dumps(new_req))
            return
            
    # Otherwise everything is set, so we just ran with the given time range        
    try:
        creds = make_credentials(*tuple(
            boto3.client('kms').decrypt(CiphertextBlob=b64decode(mcreds))['Plaintext'].decode().split(',')))
        logger.info(" Querying Sumo query {} from {} to {} using this query: {}".format(query_name,req['from'],req['to'],query))
        data = execute_search(query, creds, req, context, query_name, timerange, jobid=req.get('jobid', None), session=req.get('session', None), st=timenow,logger=logger)
        if (data is None):
            # query didn't finish on time, and was called
            logger.info("{} approaching execution limit for lambda, so self-invoke another iteration".format(query_name))
        else:
            if (len(data)>0):
                # first save data to S3
                s3_client = boto3.client('s3')
                #### DONT FORGET TO DEFINE THIS !!!
                out_bucket = os.environ.get('OUT_BUCKET')
                logger.info("Query {} from {} to {} got {} records, now saving to S3".format(query_name,req['from'],req['to'],len(data)))
                store(str(data),s3_client,out_bucket,"sumo_tech_queries_dev/{}/raw_{}".format(query_name,from_time.strftime("%Y/%m/%d/")),main_file_name="{}.dat".format(query_name),auto_timestamp = False)
                logger.info("Query {} from {} to {} done saving to S3".format(query_name,req['from'],req['to']))
                # TODO: then write data to Firehose which then passes to Redshift
                logger.info("If you want write the results to a Firehose, uncomment the line below")
                #stash.stash(data,streams)
                #logger.info("Query {} from {} to {} done saving to Firehose".format(query_name,req['from'],req['to']))
            else:
                logger.warn("Query {} from {} to {} got 0 records".format(query_name,req['from'],req['to'])) 
    except Exception as e:
        logger.error(e)
        