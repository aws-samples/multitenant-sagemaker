#from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_sagemaker as sagemaker,
    aws_lambda as _lambda,
    #CfnParameter as cfnp
)

import json
import lib.pipeline as pipeline
import os
from os import path


class SingleAccountTenantOnboardStack(core.Stack):

    def create_tenant_stepfunction(self, table_name, region, sfn_role_arn):

      #Create SFN
      with open("./SFN/CreateTenantSFN.json", "r") as fh:
        create_tenant_asl = json.load(fh)
      create_tenant_state_machine = stepfunctions.CfnStateMachine(
        self,
        "id_sm_multitenant_create_tenant_statemachine",
        role_arn=sfn_role_arn,
        definition_string=json.dumps(create_tenant_asl),
        definition_substitutions={
          "TableName": table_name,
          "LocationConstraint": region
        },
        state_machine_name="sm-multitenant-create-tenant-statemachine"
      )

    def delete_tenant_step_function(self, table_name, sfn_role_arn):

      #Delete SFN
      with open("./SFN/DeleteTenantSFN.json", "r") as fh:
        delete_tenant_asl = json.load(fh)
      delete_tenant_state_machine = stepfunctions.CfnStateMachine(
        self,
        "id_sm_multitenent_delete_tenant_step_fucntion",
        role_arn=sfn_role_arn,
        definition_string=json.dumps(delete_tenant_asl),
        definition_substitutions={
          "TableName": table_name
        },
        state_machine_name="sm-multitenant-delete-tenant-statemachine"
      )

    def deploy_endpoint_stepfunction(self, table_name, sfn_role_arn):

      #Deploy SFN
      with open("./SFN/DeployEndpointSFN.json", "r") as fh:
        deploy_endpoint_asl = json.load(fh)
      deploy_endpoint_state_machine = stepfunctions.CfnStateMachine(
        self,
        "id_sm_multitenent_deploy_tenant_step_fucntion",
        role_arn=sfn_role_arn,
        definition_string=json.dumps(deploy_endpoint_asl),
        definition_substitutions={
          "TableName": table_name
        },
        state_machine_name="sm-multitenant-deploy-tenant-statemachine"
      )

    def create_sm_pipeline(self, table, region):

      pipeline_role = iam.Role(
            self, "id_sm_pipeline_role",
            role_name = "sm-multitenant-pipeline-role",
            assumed_by = iam.ServicePrincipal('sagemaker.amazonaws.com')
        )

      function_name = "sm-multitenant-info-handler-lambda"

      tenant_info_handler_lambda = _lambda.Function(
          self, "id_tenant_info_handler_lambda_fn",
          function_name=function_name,
          code = _lambda.Code.from_asset(path.join("./lambda", "tenant_info_handler")),
          handler = "lambda_function.lambda_handler",
          runtime = _lambda.Runtime.PYTHON_3_8,
          environment={
            "TENANT_TABLE" : table.table_name
          }
      )

      table.grant_read_data(tenant_info_handler_lambda)

      pipeline_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess')
      )

      pipeline_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess')
      )

      tenant_info_handler_lambda.grant_invoke(pipeline_role)

      role_name = "arn:aws:iam::{}:role/{}".format(self.account, pipeline_role.role_name)

      pipline_def = {
        'PipelineDefinitionBody' : pipeline.get_pipeline(region, role_name, function_name).definition()
       }

      cfn_pipeline = sagemaker.CfnPipeline(self, "id_sm_multitenant_model_build_pipeline",
          pipeline_definition=pipline_def,
          pipeline_name="sm-multitenant-model-build-pipeline",
          role_arn=pipeline_role.role_arn,
          pipeline_description="sagemaker-multitenant-model-build-pipeline",
          pipeline_display_name="sagemaker-multitenant-model-build-pipeline"
      )



    def __init__(self, scope: core.Construct, construct_id: str, env, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table_name = self.node.try_get_context("table_name")
        region = self.node.try_get_context("region")
        
        if not table_name:
            raise ValueError("Please provide table name for tenant info as table_name context variable.")

        # # create a table
        table = dynamodb.Table(self, "Table",
            table_name = table_name,
            partition_key=dynamodb.Attribute(
                name="tenant-name",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=core.RemovalPolicy.DESTROY
        )

        sfn_role = iam.Role(
              self, "id_sfn_role",
              role_name = "sfn-role",
              assumed_by = iam.CompositePrincipal(iam.ServicePrincipal("states.amazonaws.com"), iam.ServicePrincipal("sagemaker.amazonaws.com"))
          )

        sfn_role.add_managed_policy(
          iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess')
        )

        sfn_role.add_managed_policy(
          iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess')
        )

        sfn_role.add_managed_policy(
          iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess')
        )

        sfn_role_arn = sfn_role.role_arn

        self.create_tenant_stepfunction(table_name, env.region, sfn_role_arn)
        self.delete_tenant_step_function(table_name, sfn_role_arn)
        self.deploy_endpoint_stepfunction(table_name, sfn_role_arn)
        self.create_sm_pipeline(table, env.region)
