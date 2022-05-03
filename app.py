#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from multitenant_sagemaker.single_account_tenant_onboard_stack import SingleAccountTenantOnboardStack

app = core.App()

env = core.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    )

SingleAccountTenantOnboardStack(app, "Single-account-MultitenantSagemakerStack", env=env)

app.synth()
