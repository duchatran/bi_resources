 Dev_BI_Sumo_Query
 ---------------------------------------------------------------- 
+ Main file:  lambda_function.py
+ Task: Runs a sumo query, saves data to S3 and (optionally) sends data to one or more  Kinesis Firehose(s). If sending to Firehose(s), pass a comma-separated string of their name(s) under the "streams" field in the payload
+ Environment Parameters: 
>
>    OUT_BUCKET  = sample-bi # target bucket to archive data to. Need to create this bucket before running this function
>
+ Sample Test Payload: lambda-payloads.json 
+ Trigger: No 
NOTE: To create an encrypted value for the cred field in the payload, you can create an Environment Variable with plain value of the format: SumoAccessID,SumoAccessKey,Deployment then encrypt in transit (see more at https://docs.aws.amazon.com/lambda/latest/dg/tutorial-env_console.html) 

