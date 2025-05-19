## This code will send reminder in slack channel to share user the weekly updates 

import os
import json
import requests

def lambda_handler(event, context):
    slack_token = os.environ['SLACK_BOT_TOKEN']
    slack_channel = os.environ['SLACK_CHANNEL_ID']
    
    message = {
        "channel": slack_channel,
        "text": "👋 *Hey team!*\n\nIt’s time for your *weekly update*.\n\nPlease share your progress along with Jira ticket numbers and a brief status. \n\n Thank you !🙌\n\n",
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {slack_token}"
    }

    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=json.dumps(message))

    if response.status_code != 200:
        raise Exception(f"Slack API error: {response.status_code} - {response.text}")

    return {
        'statusCode': 200,
        'body': json.dumps('Message sent to Slack!')
    }
