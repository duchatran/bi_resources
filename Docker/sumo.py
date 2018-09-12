from botocore.vendored import requests
import datetime
import base64
import time
import boto3
import json
import stash
import copy
import lambda_simulator

s3_client = boto3.client('s3')
#lambda_client = boto3.client('lambda')
seconds_remaining_before_re_execution = 60 # if less than 1 mins remaining and not done gathering results, start in new func.

def store(data,s3_client,out_bucket,object_prefix,main_file_name=None,auto_timestamp = True):
    """ stores data to a S3 bucket
    Args:
        :data - data to be written, should be utf8 encoded:
        :s3_client: s3 client to write
        :out_bucket: name of the destination bucket
        :object_prefix: the prefix of the target object to be uploaded to S3
    :return none
    """

    timenow = datetime.datetime.now()
    if (main_file_name is None):
        s3_obj_suffix = "data.dat"
    else:
        s3_obj_suffix = main_file_name

    file_write_name = '/tmp/tmp_{}.json'.format(timenow.strftime("%Y-%m-%d"))

    with open(file_write_name, 'w', encoding='utf8') as f:
        f.write(data)

    if (auto_timestamp):
        s3_client.upload_file(file_write_name, out_bucket,
                              '{}{}{}'.format(object_prefix, timenow.strftime("%Y/%m/%d/"), s3_obj_suffix))
    else:
        s3_client.upload_file(file_write_name, out_bucket,
                              '{}{}'.format(object_prefix, s3_obj_suffix))
    print('Uploaded file {} to bucket: {}'.format(file_write_name,out_bucket))
    return


def make_credentials(id, key, region):
    key = base64.b64encode(bytes('{}:{}'.format(id, key), 'utf8')).decode('utf8')
    return {'access_key': key, 'region': region}

def execute_search(query, creds,  req, context, query_name, timerange=None, jobid=None, session=None, st=None,logger = None):
    """ Execute a sumo query using the provided creds
        Args:
        :query - query string
        :creds - a dict with a key called "access_key" of the format: <sumo_id>:<sumo_key>
        :timerange (optional) - a dict with 2 keys: 'to' and 'from' whose values are datetime values
        :return: results
    """

    # we won't actually use execute_search for this client
    lambda_client = lambda_simulator.LambdaClient(execute_search,'execute_search')

    if not creds:
        raise Exception("invalid creds {} provided.".format(creds))

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + creds['access_key'],
        'Accept': 'application/json'
    }

    timenow = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    if (timerange is None):
        # ensure same time on any system running
        end_time = datetime.datetime.combine(datetime.date.today(), datetime.time.min) - datetime.timedelta(days=1)
        start_time = end_time - datetime.timedelta(hours=6)
    else:
        end_time = timerange['to']
        start_time = timerange['from']

    params = {
        'query': query,
        'from': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        'to': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        'timeZone': 'PST'
    }

    sumo_session = requests.session()
    # not all regions included here but us2 = BE = enough probably.

    api_endpoint = 'https://api.{}.sumologic.com/api/v1/search/jobs/'.format(creds["region"]) if creds['region'] in \
                                                                                                 ['us2', 'eu',
                                                                                                  'au'] else 'https://api.sumologic.com/api/v1/search/jobs/'
    if not jobid:
        r = sumo_session.post(api_endpoint, headers=headers, json=params)
        job_id = r.json()['id']

        r = sumo_session.get(api_endpoint + job_id, headers=headers)
        raw_state = r.json().get('state',None)
        if (raw_state is not None):
            request_state = raw_state.upper()
        else:
            if (logger is not None):
                logger.warn("State field doesn't exist. Response: {}".format(str(r)))
            else:
                print("ERROR: State field doesn't exist. Response: {}".format(str(r)))
            request_state = None

    else:
        # if jobid is not none, we have a context pass - set job_id used = jobid passed from last lambda.
        job_id = jobid
        request_state = 'GATHERING RESULTS'

    while ((request_state is not None) and (request_state not in ['PAUSED', 'FORCE PAUSED', 'DONE GATHERING RESULTS', 'CANCELED'])):
        time.sleep(10)
        out_cookies = session if session else dict(sumo_session.cookies)
        # TODO: To handle the case when some function fails to finish within 5 mins
        if context.get_remaining_time_in_millis() / 1000 < seconds_remaining_before_re_execution:
            # replicate req:
            new_req = copy.copy(req)
            new_req['jobid'] = job_id
            new_req['session'] = out_cookies
            resp = lambda_client.invoke(FunctionName=context.invoked_function_arn,
                                        InvocationType='Event',
                                        Payload=json.dumps(new_req))
            print('Query: {}, context passed to {}, timeout.'.format(req['name'],resp))
            return None
        
        r = sumo_session.get('{}{}'.format(api_endpoint, job_id), headers=headers,
                             cookies=out_cookies)
        if r.status_code != 200:
            print(f'error caught - retrying once.code: {r.status_code}, error: {r.content}')
            time.sleep(10)
            r = sumo_session.get('{}{}'.format(api_endpoint, job_id), headers=headers,
                                 cookies=out_cookies)
            print(f'RETRY>>>> endpoint: {api_endpoint}, job_id: {job_id}, cooks: {out_cookies}')
            print(f'RETRY>>>> status: {r.status_code}, resp: {r.content}')
            
        
        # end halabi debugging
        message_count = r.json().get('messageCount',None)
        if (message_count is None):
            if (logger is not None):
                logger.warn("MessageCount field doesn't exist. Response: {}".format(str(r)))
            else:
                print("ERROR: MessageCount field doesn't exist. Response: {}".format(str(r)))
            request_state = r.json().get('state',None)
            if (request_state is not None):
                request_state = request_state.upper()
            else:
                if (logger is not None):
                    logger.error("Request State is none!")
                else:
                    print("ERROR: Request State is none!")
                break
        else:
            #message_count = r.json()['messageCount']
            record_count = r.json().get('recordCount', None)
            request_state = r.json()['state'].upper()

    if ((request_state is not None) and ('DONE' in request_state)):
        # Check if we have enough time left to send data
        out_cookies = session if session else dict(sumo_session.cookies)
        count = record_count if record_count else message_count
        if (count >100000):
            time_limit = 3*seconds_remaining_before_re_execution
        else:
            time_limit = seconds_remaining_before_re_execution
        if context.get_remaining_time_in_millis() / 1000 < time_limit:
            # replicate req:
            new_req = copy.copy(req)
            new_req['jobid'] = job_id
            new_req['session'] = out_cookies
            resp = lambda_client.invoke(FunctionName=context.invoked_function_arn,
                                        InvocationType='Event',
                                        Payload=json.dumps(new_req))
            print('Query: {} finished but need more time to stash, context passed to {}, timeout.'.format(req['name'],resp))
            return None
        out = []
        co = 0
        while co < count:
            r = sumo_session.get('{}{}/records?offset={}&limit=10000'.format(api_endpoint, job_id, co), headers=headers,
                                 cookies=out_cookies)

            co += 10000  # increase offset by paging limit

            if r.json().get('records', None):
                for row in r.json()['records']:
                    new_row = row['map']
                    # execution time
                    new_row['sys_date'] = st.strftime("%Y-%m-%dT%H:%M:%S") if (st is not None) else timenow.strftime("%Y-%m-%dT%H:%M:%S")
                    # actualy query time
                    new_row['query_start'] = start_time.strftime("%Y-%m-%dT%H:%M:%S") 
                    new_row['query_end'] = end_time.strftime("%Y-%m-%dT%H:%M:%S")
                    out.append(new_row)
            else:
                for row in r.json()['messages']:
                    new_row = row['map']
                    # execution time
                    new_row['sys_date'] = st.strftime("%Y-%m-%dT%H:%M:%S") if (st is not None) else timenow.strftime("%Y-%m-%dT%H:%M:%S")
                    # actualy query time
                    new_row['query_start'] = start_time.strftime("%Y-%m-%dT%H:%M:%S")  
                    new_row['query_end'] = end_time.strftime("%Y-%m-%dT%H:%M:%S")
                    out.append(new_row)
        return out

    elif request_state in ['PAUSED', 'FORCE PAUSED', 'CANCELED']:
        et = datetime.datetime.now()
        print("Request {}.".format(request_state))
        return None
    else:
        if (request_state is None):
            # Sumo API probably crapped out so we just rerun the query
            retry= req.get('retry',0)
            if (retry <3):
                new_req = copy.copy(req)
                if ('jobid' in new_req):
                    new_req.pop('jobid')
                if ('session' in new_req):
                    new_req.pop('session')    
                new_req['retry'] = retry+1
                resp = lambda_client.invoke(FunctionName=context.invoked_function_arn,
                                        InvocationType='Event',
                                        Payload=json.dumps(new_req))
                print('Retry query: {}, timerange: {} to {},  context passed to {}, timeout.'.format(query,start_time.strftime("%Y-%m-%dT%H:%M:%S"),end_time.strftime("%Y-%m-%dT%H:%M:%S"),resp))
                return None
            else:
                print("Give up trying query {} timerange: {} to {} after {} times".format(query,start_time.strftime("%Y-%m-%dT%H:%M:%S"),end_time.strftime("%Y-%m-%dT%H:%M:%S"),retry))
                return None
        print("Error, request state was: {}.".format(request_state))
        return None



def extract_fields(data):
    return [field['name'] for field in data]