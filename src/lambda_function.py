import boto3
import os
import json

ec2 = boto3.client('ec2')
sns = boto3.client('sns')
iam = boto3.client('iam')

# Pulling variables from Environment Variables
ISOLATION_SG_ID = os.environ['ISOLATION_SG_ID']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']


def isolate_instance(finding):
    """Containment path for EC2 network threats: move the instance into the deny-all SG."""
    instance_id = finding['resource']['instanceDetails']['instanceId']
    finding_type = finding['type']

    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[ISOLATION_SG_ID]
    )
    print(f"Successfully isolated instance: {instance_id}")

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
    return f"Isolated instance {instance_id}"


def revoke_credentials(finding):
    """Containment path for IAM credential threats: disable the compromised access key."""
    finding_type = finding['type']
    access_key_details = finding['resource']['accessKeyDetails']
    username = access_key_details['userName']
    access_key_id = access_key_details['accessKeyId']

    iam.update_access_key(
        UserName=username,
        AccessKeyId=access_key_id,
        Status='Inactive'
    )
    print(f"Successfully deactivated access key {access_key_id} for user: {username}")

    alert_message = (
        f"SECURITY ALERT!\n\n"
        f"GuardDuty detected a threat: {finding_type}.\n"
        f"Access key {access_key_id} belonging to IAM user '{username}' "
        f"has been automatically deactivated.\n"
        f"Please investigate immediately."
    )
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=alert_message,
        Subject=f"URGENT: IAM Credentials Revoked for {username}"
    )
    return f"Deactivated key {access_key_id} for {username}"


def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event)}")

        finding = event['detail']
        finding_type = finding['type']

        # Route based on what kind of resource GuardDuty flagged.
        resource_type = finding.get('resource', {}).get('resourceType')

        if resource_type == 'AccessKey':
            result = revoke_credentials(finding)
        elif resource_type == 'Instance':
            result = isolate_instance(finding)
        else:
            # Unknown/unhandled finding — alert a human rather than failing silently.
            result = f"No automated action for resourceType '{resource_type}'"
            print(result)
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=(
                    f"GuardDuty finding received with no automated handler.\n"
                    f"Type: {finding_type}\nResourceType: {resource_type}"
                ),
                Subject="GuardDuty finding: manual review needed"
            )

        return {
            'statusCode': 200,
            'body': f'Success: {result}'
        }

    except Exception as e:
        print(f"Error processing event: {e}")
        raise e
