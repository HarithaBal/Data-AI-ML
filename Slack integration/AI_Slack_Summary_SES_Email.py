import boto3
import re

ses = boto3.client('ses')

def lambda_handler(event, context):
    sender = "haritha.b@cloudjournee.com"
    recipients = ["harithabal55@gmail.com"]
    
    bedrock_result = event.get("bedrockResult")
    if not bedrock_result:
        return {
            'statusCode': 400,
            'body': "No bedrockResult found"
        }
    
    # Split into blocks using the separator and strip whitespace
    blocks = [block.strip() for block in bedrock_result.split('---\n\n') if block.strip()]
    
    # Deduplicate blocks while preserving order
    seen = set()
    unique_blocks = []
    for block in blocks:
        if block not in seen:
            unique_blocks.append(block)
            seen.add(block)
    
    # Join back the unique blocks with the separator
    clean_summary = "\n\n---\n\n".join(unique_blocks)
    
    # Extract date from the first block for the email subject
    date_match = re.search(r"Subject: Team Daily Update - (\d{4}-\d{2}-\d{2})", unique_blocks[0])
    date_str = date_match.group(1) if date_match else "Unknown Date"
    
    subject = f"Team Daily Update - {date_str}"
    html_summary = clean_summary.replace("\n", "<br>")
    
    try:
        response = ses.send_email(
            Source=sender,
            Destination={'ToAddresses': recipients},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': clean_summary},
                    'Html': {'Data': html_summary}
                }
            }
        )
        return {
            'statusCode': 200,
            'body': f"Email sent successfully. Message ID: {response['MessageId']}"
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Failed to send email: {str(e)}"
        }
