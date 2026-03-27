import aws_cdk as cdk
from alb_priority_poc.alb_priority_poc_stack import AlbPriorityPocStack
import os
from dotenv import load_dotenv

load_dotenv()

app = cdk.App()
AlbPriorityPocStack(
    app, 
    "AlbPriorityPocStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION")
    )
)
app.synth()
