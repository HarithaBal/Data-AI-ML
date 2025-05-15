### This function will send the AI Generated Summary as an email to the Manager and slack users.

import boto3
import os

ses = boto3.client('ses')

def lambda_handler(event, context):
    # Replace with your verified sender and recipient emails
    sender = "haritha.b@cloudjournee.com"
    recipients = ["harithabal55@gmail.com"]

    # Subject line (could also be extracted from summary if needed)
    subject = "Team Daily Update - 2025-05-12"

    # Get the summary from Bedrock (assuming it's passed in event or fetched earlier)
    summary = event.get("summary")  # OR just assign directly if you already have it
    
    # Optional: Convert line breaks to HTML format
    html_summary = summary.replace("\n", "<br>")

    # Send email
    response = ses.send_email(
        Source=sender,
        Destination={'ToAddresses': recipients},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': summary},       # Plain text version
                'Html': {'Data': html_summary}   # HTML version
            }
        }
    )

    return {
        'statusCode': 200,
        'body': f"Email sent successfully. Message ID: {response['MessageId']}"
    }
