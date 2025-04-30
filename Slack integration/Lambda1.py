#This code will integrate slack and automate the slack appmentions triggers and fetches the data from AWS Bedrock by triggering the step function and then trigger the lambda 2 
to invoke bedrock agent

###############################################################################################################################################################################
#Environment Variables for Lambda 1:
#Key  	                                                     Value

#AGENT_ALIAS_ID											------------
#AGENT_ID												   --------------
#SLACK_BOT_ID											---------------
#SLACK_BOT_TOKEN									-------------------------------------------------------
#API Gateway URL												https://yf0b2uok08.execute-api.us-east-2.amazonaws.com/Prod/slack/events
												              https://yf0b2uok08.execute-api.us-east-2.amazonaws.com/Prod

###################################################################################################################################################################################
import json
import logging
import os
import re
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stepfunctions = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

def lambda_handler(event, context):
    logger.info("Received Slack event: %s", json.dumps(event))
    body = json.loads(event.get("body", "{}"))

    # Slack URL verification
    if "challenge" in body:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": body["challenge"]
        }

    slack_event = body.get("event", {})
    event_type = slack_event.get("type")

    # ✅ Properly indented check for app_mention only
    if event_type != "app_mention":
        logger.info("Ignoring non-app_mention event of type: %s", event_type)
        return {"statusCode": 200, "body": "Ignored non-mention event"}
    
    # Ignore bot-generated messages
    if "bot_id" in slack_event or slack_event.get("subtype") == "bot_message":
        logger.info("Bot message detected, ignoring.")
        return {"statusCode": 200, "body": "Ignoring bot message"}

    user_message = slack_event.get("text", "").strip()
    channel_id = slack_event.get("channel", "")
    user_id = slack_event.get("user", "")
    thread_ts = slack_event.get("thread_ts") or slack_event.get("ts")

    if not user_message:
        return {"statusCode": 400, "body": "No message found"}

    # Clean up @bot mentions from the message
    cleaned_message = re.sub(r"<@[\w]+>", "", user_message).strip()

    input_payload = {
        "user_id": user_id,
        "channel_id": channel_id,
        "thread_ts": thread_ts,
        "cleaned_message": cleaned_message,
        "session_id": f"slack-session-{channel_id}-{user_id}"
    }

    logger.info("Starting Step Function with input: %s", json.dumps(input_payload))
    stepfunctions.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(input_payload)
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Acknowledged!"})
    }

