BI_Orchestrator 
 ---------------------------------------------------------------- 
+ Main file:  orchestrator.py
+ Task: Invokes various functions configured in an input file. Triggered via multiple rules (BI_DailyOrchestratorTrigger for dev)
See dailyRuns.json for a sample config file
+ Environment Parameters: 
> BI_DailyOrchestratorDBNonPopularTrigger = config_files/dailyRunsDBNonPopular.json # path to config file for non-popular DBs 
> BI_DailyOrchestratorTrigger = config_files/dailyRunsDemo.json # path to config file for non-db techs
> CONFIG_BUCKET = sample-bi # bucket containing config files  
> JSON_CONFIG_FILE_NAME = config_files/dailyRunsDemo.json # backup value for config file 
> LAMBDA_FUNC_NAME = DEV_BI_SUMO_QUERY
+ Sample Test Payload: lambda-payloads.json 
+ Trigger: Yes
> BI_DailyOrchestratorTrigger:  cron(35 20 * * ? *) # A sample trigger. Each trigger name will be mapped to a config file (see EVs above)
> BI_DailyOrchestratorDBNonPopularTrigger: cron(0 15 * * ? *) # Another sample trigger 


