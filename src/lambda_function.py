import boto3
import os
import json

ec2 = boto3.client('ec2')
sns = boto3.client('sns')

# Pulling variables from Environment Variables
ISOLATION_SG_ID = os.environ['ISOLATION_SG_ID']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

print(f"DEBUG: The exact ARN being used is ->{SNS_TOPIC_ARN}<-")
def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Navigate GuardDuty JSON structure to find the Instance ID
        finding = event['detail']
        instance_id = finding['resource']['instanceDetails']['instanceId']
        finding_type = finding['type']
        
        # 1. Isolate the Instance
        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[ISOLATION_SG_ID]
        )
        print(f"Successfully isolated instance: {instance_id}")
        
        # 2. Send SNS Alert
        alert_message = (
            f"SECURITY ALERT!\n\n"
            f"GuardDuty detected a threat: {finding_type}.\n"
            f"Instance {instance_id} has been automatically isolated from the network.\n"
            f"Please investigate immediately."
        )
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=alert_message,
            Subject=f"URGENT: EC2 Instance {instance_id} Isolated"
        )
        
        return {
            'statusCode': 200,
            'body': 'Successfully isolated instance and sent alert.'
        }
        
    except Exception as e:
        print(f"Error processing event: {e}")
        raise e
