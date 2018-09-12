import lambda_simulator
import sumo_query_function
import orchestrator
import json

# Load up functions to be called
lambda_client = lambda_simulator.LambdaClient(sumo_query_function.lambda_handler,'sample_query')
lambda_client = lambda_simulator.LambdaClient(orchestrator.lambda_handler,'orchestrator')
lambda_client.invoke('orchestrator','Sync',json.dumps({}))

