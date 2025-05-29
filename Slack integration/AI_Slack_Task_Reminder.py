#This file will fetches all the pending Jira tasks tagged to user in Slack and notifys users  in Slack channel on Scheduled or 
#Cron Job basis or Trigger basis.

import os
import requests
from collections import defaultdict

JIRA_DOMAIN = os.environ['JIRA_DOMAIN']
JIRA_EMAIL = os.environ['JIRA_EMAIL']
JIRA_API_TOKEN = os.environ['JIRA_API_TOKEN']
SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
SLACK_CHANNEL_ID = os.environ['SLACK_CHANNEL_ID']

# Mapping Jira AccountID to Slack User ID 
JIRA_ACCOUNTID_TO_SLACK = {
    "5f34e6923e9e2e004dafc9ba": "U08MHUM0AL9",  # Haritha Bal
    "712020:0275b971-e1c1-4303-b06c-96d4300fa667": "U08L161896J"  # Haritha
}


def get_pending_jira_tasks():
    jql = "project = SCRUM AND sprint in openSprints() AND statusCategory != Done"
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    params = {
        "jql": jql,
        "fields": "summary,assignee,key,priority"
    }
    response = requests.get(url, headers=headers, auth=auth, params=params)
    response.raise_for_status()
    return response.json()["issues"]


def group_tasks_by_assignee(issues):
    tasks = defaultdict(lambda: defaultdict(list))

    priority_map = {
        "Highest": "P1",
        "High": "P2",
        "Medium": "P3",
        "Low": "P4",
        "Lowest": "P5"
    }

    for issue in issues:
        assignee = issue["fields"]["assignee"]
        if not assignee:
            continue

        account_id = assignee.get("accountId")
        if account_id not in JIRA_ACCOUNTID_TO_SLACK:
            print(f"[WARN] No Slack mapping for Jira account ID: {account_id}")
            continue

        slack_id = JIRA_ACCOUNTID_TO_SLACK[account_id]
        key = issue["key"]
        summary = issue["fields"]["summary"]
        priority = issue["fields"].get("priority", {}).get("name", "No Priority")
        normalized_priority = priority_map.get(priority, priority)
        url = f"https://{JIRA_DOMAIN}/browse/{key}"

        task_text = f"- 🔹 <{url}|{key}>: {summary} ({normalized_priority})"
        tasks[slack_id][normalized_priority].append(task_text)

    return tasks


def format_slack_message(tasks_by_user):
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "*✅ Pending Tasks for Current Sprint*"}}]
    priority_order = ["P1", "P2", "P3", "P4", "P5"]

    for slack_id, priorities in tasks_by_user.items():
        message_lines = []
        for prio in priority_order:
            if prio in priorities:
                message_lines.append(f"*Priority {prio}:*")
                message_lines.extend(priorities[prio])
        other_prios = set(priorities.keys()) - set(priority_order)
        for prio in sorted(other_prios):
            message_lines.append(f"*Priority {prio}:*")
            message_lines.extend(priorities[prio])

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"👤 <@{slack_id}>\n" + "\n".join(message_lines)}
        })
        blocks.append({"type": "divider"})

    return blocks


def post_to_slack(blocks):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": SLACK_CHANNEL_ID,
        "blocks": blocks,
        "text": "Pending Jira tasks"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()


def lambda_handler(event, context):
    issues = get_pending_jira_tasks()
    tasks_by_user = group_tasks_by_assignee(issues)
    if not tasks_by_user:
        print("No tasks to report.")
        return {"statusCode": 200, "body": "No tasks found."}

    blocks = format_slack_message(tasks_by_user)
    post_to_slack(blocks)
    return {"statusCode": 200, "body": "Notification sent to Slack."}
