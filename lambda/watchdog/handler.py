import os
import boto3
import urllib3
import json

# Environment variables (injected by Terraform)
WORKER_INSTANCE_ID = os.environ['WORKER_INSTANCE_ID']
HEALTHCHECK_URL = os.environ['HEALTHCHECK_URL']

# AWS EC2 client
ec2_client = boto3.client('ec2')

# HTTP client
http = urllib3.PoolManager()

def check_laptop_health():
    """Check if laptop is UP via HTTPS healthcheck (Tailscale Funnel)"""
    try:
        response = http.request('GET', HEALTHCHECK_URL, timeout=10.0)
        return response.status == 200
    except Exception as e:
        print(f"Error checking laptop healthcheck: {e}")
        return False

def get_ec2_state():
    """Get current EC2 instance state"""
    response = ec2_client.describe_instances(InstanceIds=[WORKER_INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state

def start_ec2():
    """Start EC2 instance"""
    print(f"Starting EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.start_instances(InstanceIds=[WORKER_INSTANCE_ID])

def stop_ec2():
    """Stop EC2 instance"""
    print(f"Stopping EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.stop_instances(InstanceIds=[WORKER_INSTANCE_ID])

def lambda_handler(event, context):
    """
    Lambda entry point - Watchdog logic

    Rules:
    - Laptop UP + EC2 running -> Stop EC2 (save costs)
    - Laptop DOWN + EC2 stopped -> Start EC2 (failover)
    - Otherwise -> Do nothing
    """

    # Check laptop state
    laptop_up = check_laptop_health()
    print(f"Laptop status: {'UP' if laptop_up else 'DOWN'}")

    # Check EC2 state
    ec2_state = get_ec2_state()
    print(f"EC2 state: {ec2_state}")

    # Decision logic
    if laptop_up and ec2_state == 'running':
        stop_ec2()
        action = "Stopped EC2 (laptop is back up)"
    elif not laptop_up and ec2_state == 'stopped':
        start_ec2()
        action = "Started EC2 (laptop is down)"
    elif laptop_up and ec2_state == 'stopped':
        action = "None (normal state - laptop up, EC2 stopped)"
    elif not laptop_up and ec2_state == 'running':
        action = "None (failover active - laptop down, EC2 running)"
    else:
        action = f"None (EC2 in transitional state: {ec2_state})"
    
    print(f"Action: {action}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'laptop_up': laptop_up,
            'ec2_state': ec2_state,
            'action': action
        })
    }