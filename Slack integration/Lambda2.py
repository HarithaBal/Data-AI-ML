##The lambda function will invoke the Bedrock Agent and process and respond back to slack

#Environment Variables

#AGENT_ALIAS_ID            ---------------
#AGENT_ID                  ---------------
#SLACK_BOT_TOKEN           -----------------------------------------------
#########################################################################################################################

import json
import os
import logging
import boto3
import urllib3
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-agent-runtime")
http = urllib3.PoolManager()

AGENT_ID = os.environ["AGENT_ID"]
AGENT_ALIAS_ID = os.environ["AGENT_ALIAS_ID"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

def lambda_handler(event, context):
    logger.info("Step Function input: %s", json.dumps(event))
    session_id = event["session_id"]
    message = event["cleaned_message"]
    channel_id = event["channel_id"]
    user_id = event["user_id"]
    thread_ts = event["thread_ts"]

    try:
        response_stream = bedrock.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message,
            endSession=False
        )

        final_response = extract_event_stream_response(response_stream)
        send_to_slack(channel_id, final_response, thread_ts, user_id)

    except Exception as e:
        logger.error(f"Error during Bedrock invocation: {e}")
        send_to_slack(channel_id, "⚠️ Error processing your request.", thread_ts, user_id)

    return {"status": "completed"}

def extract_event_stream_response(response):
    chunks = []
    for event in response["completion"]:
        if "chunk" in event and "bytes" in event["chunk"]:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
    return " ".join(chunks).strip() if chunks else "No meaningful response from agent."

def send_to_slack(channel, message, thread_ts=None, user_id=None):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    if user_id:
        message = f"<@{user_id}> {message}"
    payload = {"channel": channel, "text": message}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    for attempt in range(3):
        try:
            resp = http.request("POST", url, body=json.dumps(payload), headers=headers)
            logger.info(f"Slack response: {resp.status}, {resp.data.decode('utf-8')}")
            if resp.status != 429:
                break
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return None
