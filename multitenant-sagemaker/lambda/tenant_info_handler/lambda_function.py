# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import os

dynamodb = boto3.client('dynamodb')

table_name = os.environ.get("TENANT_TABLE")

def lambda_handler(event, context):
   print(event)
   
   tenant_name = event['tenant-name']
   
   if(tenant_name is None):
      raise ValueError("Tenant name is required.")
      
   response = dynamodb.get_item(TableName=table_name, Key={'tenant-name':{'S':tenant_name}})
   
   if 'Item' not in response:
      raise ValueError("Teanant with given name does not exists.")
      
   tenant =  response['Item']
   
   if(tenant == None):
      raise ValueError("No tenant found wiht name {}.".format(tenant_name))

   print(tenant)
    
   return {
        "status" : "success",
        "tenant_data_location" : tenant["tenant-bucket"]["S"],
        "tenant_model_package_group" : tenant["tenant-modelregistry"]["S"]
   } 