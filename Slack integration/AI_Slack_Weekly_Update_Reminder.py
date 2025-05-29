import os
import json
import requests
import boto3 

stepfunctions = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STEP_FUNCTION_ARN"]
slack_token        = os.environ['SLACK_BOT_TOKEN']
slack_channel      = os.environ['SLACK_CHANNEL_ID']

def lambda_handler(event, context):
    print("Lambda invoked with event:", json.dumps(event))

    # Step 1: Send Slack reminder message  
    message = {
        "channel": slack_channel,
        "text": "👋 *Hey team!*\n\nIt’s time for your *weekly update*.\n\nPlease share your progress along with Jira ticket numbers and a brief status. \n\n Thank you !🙌\n\n",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {slack_token}"
    }
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers=headers,
        data=json.dumps(message)
    )
    print("Slack API response status:", response.status_code)
    print("Slack API response body:", response.text)

    if response.status_code != 200:
        raise Exception(f"Slack API error: {response.status_code} - {response.text}")

    print("Slack message sent successfully.")

    # Step 2: Trigger Step Function
    step_input = {
        "channel":   slack_channel,
        "timestamp": json.loads(response.text).get("ts"),
        "message":   message["text"]
    }

    # Debug prints before starting execution
    print("About to start Step Function execution")
    print("State Machine ARN:", STATE_MACHINE_ARN)
    print("Step Function input:", json.dumps(step_input))

    try:
        execution = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(step_input)
        )
        # Confirm it actually returned an execution ARN
        print("Started Step Function: executionArn =", execution.get("executionArn"))
    except Exception as e:
        print("Failed to start Step Function, exception:", str(e))
        raise

    return {
        'statusCode': 200,
        'body': json.dumps('Reminder sent and Step Function triggered.')
    }
