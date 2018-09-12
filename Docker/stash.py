import boto3
import json
import time
import itertools

client = boto3.client('firehose')

def stream_selector(list_of_streams):
    # next()
    return itertools.cycle(list_of_streams)

def stash(data, stream_names):
    """
    shove data into firehose stream
    :param data: standard dict.
    ################ WARNING ###############
    Dict keys HAVE to match redshift column names (order doesn't matter) excluding sys generated columns (insertion time etc).
    :return: error if error else nada.

    random notes/todos:
    For US East (N. Virginia), US West (Oregon), and EU (Ireland): 5,000 records/second, 2,000 transactions/second, and 5 MB/second.
    For US East (Ohio), US West (N. California), Asia Pacific (Singapore), Asia Pacific (Sydney), Asia Pacific (Tokyo), and EU (Frankfurt): 1,000 records/second, 1,000 transactions/second, and 1 MB/second.
    When Kinesis Data Streams is configured as the data source, this limit doesn't apply, and Kinesis Data Firehose scales up and down with no limit.
    Each Kinesis data delivery stream stores data records for up to 24 hours in case the delivery destination is unavailable.
    The maximum size of a record sent to Kinesis Data Firehose, before base64-encoding, is 1,000 KB.
    The PutRecordBatch operation can take up to 500 records per call or 4 MB per call, whichever is smaller. This limit cannot be changed.
    - > Work around limitations/ensure no throttling/dropping of records
        Could use api to check stream status and ensure not at limits but simplest for now is - multiple firehose streams, spread requests evenly over streams.
        Alternative -> can spin up one kinesis stream with x shards and do basically the same thing but using multiple shards rather than multiple streams (will still also require manual
        lambda puts or another firehose stream, bit more work not sure of cost difference, effectively same).
    """

    print('initiating stashing on streams {}'.format(stream_names))
    stream_name = stream_selector(stream_names) # this will round robin over list_of_streams

    # this does NOT catch all the ways you could mess this up - please don't be dumb.

    if type(data) != dict:
        if type(data) != list:
            #not dict, not list
            raise TypeError('Must pass dict or list of dicts to stash.stash - received data is neither.')
        else:
            #not dict, IS list, are all items dicts?
            check = set(type(i) for i in data)
            if len(check) > 1:
                #more than one type in list = bad, expecting dicts
                out = [i for i in check if i is not dict]
                raise TypeError(f'list received contains non-dict items: {out}')
    else:
        #is dict
        put_data(data, next(stream_name))
        time.sleep(.1)


    if len(data) > 500 and type(data) == list: # unlikely but could have many keys - ensure its a list we are looking at
        for batch in chunker(data, 500):
            for chunked_data in chunker(batch,int(len(batch)/len(stream_names))):
                # technically depending on other feeds to a stream we could be drastically undercutting full bandwidth.
                # ideally use a server/lambda w/ sqs to pipe requests to appropriate streams at appropriate rates.
                put_data(chunked_data, next(stream_name))
            time.sleep(.1) # math, assuming US-East nv -> 5k reqs/sec / 500/put = 10 batch per sec
            # at 1m records would take 3.3 mins to unload them all.
            # our largest dumps currently have just under 300k records or about 1 minute to fully load.
            # our sumo loader will always have ~2 mins left by design at a minimum when entering the "kinesis dump" phase
            # therefore we should be good for now but care should be taken going forward.
            # the above is assuming one stream - ever table should have 2 minimum to ensure we never approach any throttling.
    else:
        if (len(data)<20):
            # if less than 20 records then just write to one stream
            put_data(data,next(stream_name))
        else:
            for chunked_data in chunker(data,int(len(data)/len(stream_names))): #evenly split even for small numbers just in case being hit by other stream!
                # technically depending on other feeds to a stream we could be drastically undercutting full bandwidth.
                # ideally use a server/lambda w/ sqs to pipe requests to appropriate streams at appropriate rates.
                put_data(chunked_data, next(stream_name))


def chunker(data, size):
    size = size if size>0 else 1
    for i in range(0, len(data), size):
        yield data[i:i + size]

def put_data(data, stream_name):
    # todo - implement retry/backoff logic. raising the exception which would have been raised is mostly useless. Should take failed puts if any, and then reput if possible,
    # depending on error code.
    try:
        response = client.put_record_batch(
            DeliveryStreamName=stream_name,
            Records=[{'Data':json.dumps(i)} for i in data]
        )
        print(len(data), ' stashed with result:{}'.format(response['FailedPutCount']))
        if int(response.get('FailedPutCount', 0)) > 0:
            print(f'Load errors on data set {data}.')
            print(response['RequestResponses'])

        else:
            print('successful stream load.')

    except Exception as e:
        print(f'error {e} in loading data: {data}')
        raise Exception(str(e))
