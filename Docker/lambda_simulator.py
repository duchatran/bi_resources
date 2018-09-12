import datetime
import json

class LambdaClient:
   """
   This class is a simulator for the lambda client. For each Lambda function that needs to be called, a LambdaClient has to be defined upfront
   For example: if Lambda function Foo defines its handler foo_handler inside Foo.py, one need to define:
   lambda_client = LambdaClient(Foo.foo_handler,'Foo')
   """
   # Class variable to store the map of Lambda function names and their corresponding function handlers
   function_map = {}

   def __init__(self,handle_name,function_arn):
      self._handle_name = handle_name
      self._function_arn = function_arn
      LambdaClient.function_map[function_arn] = self._handle_name
      print(f"Adding {function_arn} to function handler map")

   def insert_handler(self,function_name, function_handler):
      self._function_map[function_name] = function_handler


   def invoke(self,FunctionName, InvocationType,Payload):
      context = Context(FunctionName)
      payload_obj = json.loads(Payload)
      if (not FunctionName in LambdaClient.function_map):
         raise Exception(f"{FunctionName} doesn't exist")
      else:
         LambdaClient.function_map[FunctionName](payload_obj,context)


   def set_running_time(self,runtime_msec):
      if (runtime_msec>0):
         self._runtime = runtime_msec

class Context:
   def __init__(self,invoked_function_arn):
      self.invoked_function_arn = invoked_function_arn
      self._start_time = datetime.datetime.utcnow()
      self._runtime= 86400000 # 1 day running time
      self.function_name = invoked_function_arn
      self.function_version = '0.1'
      self.memory_limit_in_mb = 1024
      self.aws_request_id = 0
      self.log_group_name=''
      self.log_stream_name=''
      self.identify=None
      self.client_context = None


   def set_running_time(self,runtime_msec):
      if (runtime_msec>0):
         self._runtime = runtime_msec

   def get_remaining_time_in_millis(self):
      return int(self._runtime-((datetime.datetime.utcnow() - self._start_time).total_seconds()*1000))



