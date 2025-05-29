import os
import json
import urllib3

# Initialize the urllib3 PoolManager
http = urllib3.PoolManager()

# Retrieve environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

def lambda_handler(event, context):
    try:
        # Extract 'summary' and 'trigger_ts' from the event
        summary = event.get("summary", "")
        thread_ts = event.get("trigger_ts", "")

        # Split the summary into entries using the delimiter
        entries = summary.split("\n\n---\n\n")

        # Remove duplicate entries while preserving order
        seen = set()
        unique_entries = []
        for entry in entries:
            cleaned_entry = entry.strip()
            if cleaned_entry and cleaned_entry not in seen:
                seen.add(cleaned_entry)
                unique_entries.append(cleaned_entry)

        # Reconstruct the cleaned summary
        cleaned_summary = "\n\n---\n\n".join(unique_entries)

        # Construct the message to be sent to Slack
        message = f"*Here is your daily summary:*\n{cleaned_summary}"

        # Prepare the payload for the Slack API
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message,
            "thread_ts": thread_ts
        }

        # Define headers for the HTTP request
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }

        # Send the POST request to Slack
        slack_url = "https://slack.com/api/chat.postMessage"
        response = http.request(
            "POST",
            slack_url,
            body=json.dumps(payload),
            headers=headers
        )

        # Decode the response data
        response_data = response.data.decode("utf-8")

        # Attempt to parse the response as JSON
        try:
            response_json = json.loads(response_data)
        except json.JSONDecodeError:
            response_json = {"error": "Invalid JSON response from Slack", "raw_response": response_data}

        # Log the response
        print("Slack post response:", response_json)

        return {"status": "posted", "response": response_json}

    except Exception as e:
        # Handle any unexpected exceptions
        print("Error occurred:", str(e))
        return {"status": "error", "message": str(e)}
