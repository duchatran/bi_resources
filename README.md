# bi_resources
Bootstrap resources to start your own data warehouse with Sumo Logic and Serverless computing. First you need to setup all roles - see IAM_Policies for needed policies and roles.
After that you can setup the functions below.

+ Dev_BI_Sumo_Query: Sample function to execute a Sumo query and save data to S3. It can also send the results to Firehose(s)   
See the README file under the folder for setting up the function. 

+ BI_Orchestrator: Once you have setup Dev_BI_Sumo_Query successfully, you can setup BI_Orchestrator to execute multiple configurable queries.
This config file uses the same data as the test payload (lambda-payloads.json) for Dev_BI_Sumo_Query
See the README file there for details.

