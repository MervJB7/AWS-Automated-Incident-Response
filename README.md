# AWS Automated Incident Response Pipeline

## Objective
This project builds an event-driven security pipeline to automatically detect and isolate compromised EC2 instances within a VPC. It demonstrates core cloud security principles, network automation, and Identity & Access Management (IAM) using AWS serverless technologies. By automating the containment phase, this architecture drastically reduces Mean Time To Respond (MTTR) from hours to seconds.

This repository also serves as a hands-on workshop designed for the Broward College Cybersecurity Club to teach members practical cloud threat containment and foundational skills for network development and security engineering.

## Architecture
![AWS Automated Incident Response Architecture](images/architecture-diagram.png) 
*(Note: Replace this image with your actual diagram in the images folder!)*

## Tools & Services Used
* **Amazon GuardDuty:** Continuous threat detection and malicious IP monitoring using machine learning.
* **Amazon EventBridge:** Serverless event routing and alert filtering.
* **AWS Lambda:** Serverless compute to execute the Python containment script.
* **Amazon SNS:** Automated email paging for the incident response team.
* **AWS IAM:** Principle of least privilege role creation for Lambda execution.
* **Amazon EC2 & VPC Security Groups:** The target asset and stateful network firewalls used for dynamic quarantine.

## The Incident Response Workflow
1. **Detection:** GuardDuty monitors VPC flow logs and identifies an EC2 instance communicating with a known malicious IP address.
2. **Routing:** EventBridge intercepts the GuardDuty finding. If it matches our custom rule for EC2 network threats, it routes the payload to Lambda.
3. **Containment:** A Python script (via Boto3) extracts the Instance ID and immediately modifies the instance's network attributes, moving it into an empty "Isolation" Security Group that implicitly denies all inbound and outbound traffic.
4. **Notification:** Lambda publishes an alert to an SNS topic, sending an immediate email notification to the security team with the compromised Instance ID.

---

## Step-by-Step Guide

### Step 1: Prepare the Infrastructure (The Victim and the Jail)
1. Launch a basic Amazon Linux EC2 instance. Leave it in its default Security Group. Note the `Instance ID`.
2. Navigate to **Security Groups** and create a new one named `Isolation-SG`. 
    **Crucial Step:** Do *not* add any Inbound or Outbound rules. An empty Security Group acts as a quarantine by dropping all network connections. Note the `Security Group ID`.

### Step 2: Set Up Amazon SNS (The Pager)
1. In the SNS Dashboard, create a **Standard** topic named `Security-Alerts`.
2. Create a subscription, choose **Email**, and enter your email address. Confirm the subscription in your inbox.
3. Note the **Topic ARN**. 
    *Troubleshooting Tip:* Ensure you copy the *Topic ARN*, not the *Subscription ARN* (which has a long UUID at the end). Using the Subscription ARN will cause Lambda to crash later with an `Invalid parameter: Topic Name` error.

### Step 3: Create the IAM Role for Lambda
1. In IAM, create a new role for the **Lambda** use case.
2. Attach the `AWSLambdaBasicExecutionRole` policy.
3. Once the role is created, add an **Inline Policy** using the JSON file located in `policies/iam_role_policy.json` in this repository. This explicit allow-list grants Lambda permission to modify EC2 security groups and publish to SNS.

### Step 4: Deploy the Lambda Function (The Brain)
1. Create a new Lambda function using **Python 3.12** and attach the IAM role from Step 3.
2. Paste the Python code located in `src/lambda_function.py`.
3. Under the **Configuration -> Environment variables** tab, add two keys:
   * `ISOLATION_SG_ID` = [Your Security Group ID]
   * `SNS_TOPIC_ARN` = [Your SNS Topic ARN]
   * *Troubleshooting Tip:* Do not use quotation marks around your environment variables.

### Step 5: Configure EventBridge (The Dispatcher)
1. Ensure GuardDuty is enabled in your account.
2. In EventBridge, create a new rule named `GuardDuty-EC2-Malicious-IP`.
3. Set the Event Pattern using the custom JSON located in `policies/eventbridge_rule.json`. This filters the noise and ensures the rule only fires for high-severity EC2 network threats (like Trojans or unauthorized access).
4. Set the target to your Lambda function.

### Step 6: Test the Pipeline
1. Navigate to the Lambda function and configure a new test event.
    **Do not use the default "Hello World" test event.** The Python script specifically looks for the `detail` dictionary key. Using the default test will result in a `KeyError: 'detail'`.

3. Paste the simulated GuardDuty finding below, replacing the placeholder with your real EC2 Instance ID:
```json
{
  "detail": {
    "type": "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom",
    "resource": {
      "instanceDetails": {
        "instanceId": "i-YOUR_REAL_INSTANCE_ID"
      }
    }
  }
}

---
----
