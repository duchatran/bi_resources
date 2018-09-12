Dockerization
----------------------------------------------------------------- 
This folder contains resources to dockerize our two Lambda functions with little refactoring. The main refactoring lies with wrapping all calls to lambda.invoke(). 
 
+ Environment Parameters: need to pass the following environment variables to the container, similar to what are needed for Orchestrator and Sumo Query functions 
>    OUT_BUCKET  = sample-bi # target bucket to archive data to. Need to create this bucket before running this function

>    JSON_CONFIG_FILE_NAME = config_files/dailyRunsDemo.json # path to config file

>    LAMBDA_FUNC_NAME = sample_query # Name of the function to query Sumo

>    CONFIG_BUCKET = sample-bi # bucket containing config files  

Before creating an image, you can simply test your packaging by running (also remember to define the EVs above before running):

python3 orchestrator_wrapper.py
