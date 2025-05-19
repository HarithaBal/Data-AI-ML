import os
import json
import urllib3
from datetime import datetime
import boto3
import re

# Environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]
BEDROCK_REGION = os.environ["REGION"]
BOT_USER_ID = os.environ["BOT_USER_ID"]
MAX_MESSAGES = 3

http = urllib3.PoolManager()
bedrock = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Parse and validate the Slack event
        slack_event = json.loads(event['body'])
        
        if not (slack_event.get('type') == 'event_callback' and 
                slack_event['event'].get('type') == 'app_mention'):
            print("Not an app_mention event")
            return {"statusCode": 200}

        slack_msg = slack_event['event']
        print("Processing message from:", slack_msg.get('user'))
        
        # Validate bot mention and command
        if not (f"<@{BOT_USER_ID}>" in slack_msg.get('text', '') and 
                "summarize" in slack_msg.get('text', '').lower()):
            print("Bot not properly mentioned")
            return {"statusCode": 200}

        # Get message history
        trigger_ts = slack_msg.get('ts')
        print(f"Fetching messages before timestamp: {trigger_ts}")
        
        response = http.request(
            'GET',
            f'https://slack.com/api/conversations.history?channel={SLACK_CHANNEL_ID}&limit={MAX_MESSAGES+1}&latest={trigger_ts}&inclusive=false',
            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
        )
        
        if response.status != 200:
            error_msg = f"Slack API error: {response.status} - {response.data.decode('utf-8')}"
            print(error_msg)
            raise Exception(error_msg)
            
        messages = json.loads(response.data.decode('utf-8')).get('messages', [])
        print(f"Found {len(messages)} raw messages")

        # Create user ID to name mapping
        user_names = {}
        user_data_cache = {}
        
        for msg in messages:
            if 'user' not in msg:
                continue
                
            user_id = msg['user']
            if user_id not in user_names:
                try:
                    if user_id not in user_data_cache:
                        user_info = http.request(
                            'GET',
                            f'https://slack.com/api/users.info?user={user_id}',
                            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                        )
                        user_data = json.loads(user_info.data)
                        user_data_cache[user_id] = user_data
                    else:
                        user_data = user_data_cache[user_id]
                    
                    if user_data.get('ok'):
                        profile = user_data['user'].get('profile', {})
                        # Try different name fields in order of preference
                        display_name = (
                            profile.get('display_name_normalized') or
                            profile.get('display_name') or
                            profile.get('real_name_normalized') or
                            profile.get('real_name') or
                            profile.get('email', '').split('@')[0].capitalize() or
                            user_id  # final fallback
                        )
                        # Clean the name - remove special characters
                        clean_name = re.sub(r'[^a-zA-Z]', '', display_name)
                        user_names[user_id] = clean_name
                        print(f"Mapped {user_id} to {clean_name}")
                    else:
                        user_names[user_id] = user_id[:3]  # Fallback to first 3 chars of user ID
                except Exception as e:
                    print(f"Error fetching user info for {user_id}: {str(e)}")
                    user_names[user_id] = user_id[:3]  # Fallback

        # Process messages
        user_messages = []
        seen_messages = set()
        
        for msg in messages:
            if msg.get('bot_id') or msg.get('subtype') == 'bot_message':
                continue
                
            if 'user' not in msg or 'text' not in msg:
                continue
                
            text = msg['text'].strip()
            user = msg['user']
            
            if not text or f"<@{BOT_USER_ID}>" in text:
                continue
                
            message_hash = hash(f"{user}:{text.lower()}")
            if message_hash in seen_messages:
                continue
                
            seen_messages.add(message_hash)
            user_messages.append({
                'user': user_names.get(user, user[:3]),
                'text': text,
                'ts': msg.get('ts')
            })

        if not user_messages:
            post_to_slack("No user messages found to summarize", trigger_ts)
            return {"statusCode": 200}

        # Generate summary
        input_text = "\n".join([f"{msg['user']}: {msg['text']}" for msg in user_messages[:3]])
        raw_summary = call_bedrock_model(input_text)
        
        # Post-processing
        clean_summary = re.sub(r'(?s)ANSWER:.*?Subject:', 'Subject:', raw_summary)
        clean_summary = re.sub(r'(?s)(Subject:.*?AI Assistant).*', r'\1', clean_summary)
        
        # Ensure names are preserved
        for msg in user_messages:
            original_name = msg['user']
            clean_summary = re.sub(
                rf'(\n|^)\s*[A-Za-z]*{original_name[0]}[A-Za-z]*:',
                f'\n{original_name}:',
                clean_summary
            )
        
        clean_summary = re.sub(r'User U\d\w+: ', '', clean_summary)
        clean_summary = re.sub(r'\n{3,}', '\n\n', clean_summary.strip())
        
        post_to_slack(clean_summary, trigger_ts)
        return {"statusCode": 200}

    except Exception as e:
        print(f"Error in handler: {str(e)}")
        post_to_slack("⚠️ Error generating summary. Please try again.", slack_msg.get('ts'))
        return {"statusCode": 500}


def call_bedrock_model(user_input):
    try:
        prompt = f"""Create a professional team update email using EXACTLY these updates:

{user_input}

FORMAT EXACTLY LIKE THIS:
Subject: Team Daily Update - {datetime.now().strftime('%Y-%m-%d')}

[Name from input EXACTLY as shown above]:
- [Bullet point 1] (Ticket: #XXX if applicable)
- [Bullet point 2]

Key Accomplishments:
- [Major achievement 1]

Ongoing Work:
- [Current task]

AI Assistant

RULES:
1. USE PROVIDED NAMES EXACTLY AS THEY APPEAR IN THE INPUT - DO NOT MODIFY THEM
2. NEVER show reasoning steps
3. ONLY include the final formatted email
4. OMIT all explanations and notes
5. If no ongoing work/blockers, keep sections with "-" 
6. PRESERVE original ticket numbers exactly
7. TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}
8. DO NOT include "Hello Team" or similar greetings
9. LIST each person's updates under their name with "-" bullet points
10. NEVER convert names to User IDs - USE THE NAMES EXACTLY AS PROVIDED

EXAMPLE OUTPUT:
Subject: Team Daily Update - 2025-05-15

H:
- Fixed login system (Ticket: #TB4532)

Har:
- Resolved S3 upload error (Ticket: #TB1257)

Key Accomplishments:
- Closed 2 critical tickets

Ongoing Work:
-

AI Assistant

NOW CREATE THE SUMMARY FOLLOWING THESE RULES EXACTLY:"""

        body = {
            "prompt": prompt,
            "max_gen_len": 1024,
            "temperature": 0.2,
            "top_p": 0.7
        }

        response = bedrock.invoke_model(
            modelId="us.meta.llama3-2-11b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        summary = response_body["generation"] if "generation" in response_body else str(response_body)
        
        # Validate tickets
        original_tickets = set(re.findall(r"#\w+", user_input))
        summary_tickets = set(re.findall(r"#\w+", summary))
        
        if not summary_tickets.issubset(original_tickets):
            return "⚠️ Summary validation failed - unexpected ticket numbers detected"
            
        return summary.strip() if summary else "No summary could be generated."

    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        return f"Error generating summary: {str(e)}"


def post_to_slack(message, thread_ts=None):
    try:
        if not message or not isinstance(message, str):
            message = "No summary content was generated"
            
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message,
            "thread_ts": thread_ts,
            "mrkdwn": True
        }

        response = http.request(
            'POST',
            "https://slack.com/api/chat.postMessage",
            body=json.dumps(payload).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json"
            }
        )

        if response.status != 200:
            raise Exception(f"Slack API error: {response.status} - {response.data}")

    except Exception as e:
        print(f"Error posting to Slack: {str(e)}")
        raise
