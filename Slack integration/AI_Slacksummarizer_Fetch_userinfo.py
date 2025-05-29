import os
import json
import urllib3

# Environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]
BOT_USER_ID = os.environ["BOT_USER_ID"]

http = urllib3.PoolManager()

def lambda_handler(event, context):
    print("Input event:", json.dumps(event))

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    def fetch_all_messages(channel_id):
        """Fetch all messages from the Slack channel with pagination."""
        all_messages = []
        cursor = None

        while True:
            url = f"https://slack.com/api/conversations.history?channel={channel_id}"
            if cursor:
                url += f"&cursor={cursor}"
            response = http.request("GET", url, headers=headers)
            if response.status != 200:
                print(f"Slack API error: {response.status}")
                break

            data = json.loads(response.data.decode("utf-8"))
            msgs = data.get("messages", [])
            all_messages.extend(msgs)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return all_messages

    # Step 1: Find the latest reminder message (loose matching, ignore bot_id)
    def get_latest_reminder_timestamp():
        messages = fetch_all_messages(SLACK_CHANNEL_ID)

        for msg in messages:
            text = msg.get("text", "").lower()
            print(f"Checking message ts={msg.get('ts')}: {repr(text)} bot_id={msg.get('bot_id')}")
            if "time for your weekly update" in text:
                print(f"Found reminder message at ts={msg.get('ts')}")
                return msg.get("ts")
        return None

    reminder_ts = get_latest_reminder_timestamp()
    if not reminder_ts:
        print("Reminder message not found.")
        return {
            "user_messages": [],
            "input_text": "",
            "error": "Reminder message not found"
        }

    print(f"Using reminder timestamp: {reminder_ts}")

    # Step 2: Fetch user messages after the reminder
    messages = fetch_all_messages(SLACK_CHANNEL_ID)
    user_msgs = []
    seen_users = set()

    for msg in messages:
        msg_ts = msg.get("ts")
        user_id = msg.get("user", "")
        text = msg.get("text", "")
        subtype = msg.get("subtype", "")

        if (not user_id               # no user (e.g. join messages)
            or subtype               # skip subtypes
            or msg.get("bot_id")     # skip bot messages
            or user_id == BOT_USER_ID
            or msg_ts <= reminder_ts
            or user_id in seen_users):
            continue

        # Fetch user's real name
        user_info_url = f"https://slack.com/api/users.info?user={user_id}"
        user_info_response = http.request("GET", user_info_url, headers=headers)
        if user_info_response.status != 200:
            username = user_id
        else:
            username = json.loads(user_info_response.data.decode("utf-8")).get("user", {}).get("real_name", user_id)

        formatted = f"{username}: {text}"
        print(f"Collected: {formatted}")
        user_msgs.append(formatted)
        seen_users.add(user_id)

    input_text = "\n".join(user_msgs)

    print("\n===== Final Logs =====")
    print("User Messages List:")
    print(user_msgs)
    print("\nCombined Input Text:")
    print(input_text)
    print("======================\n")

    return {
        "reminder_timestamp": reminder_ts,
        "user_messages": user_msgs,
        "input_text": input_text
    }
