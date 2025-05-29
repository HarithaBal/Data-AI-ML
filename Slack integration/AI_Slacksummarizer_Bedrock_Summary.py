import os
import boto3
import json
import re
from datetime import datetime

bedrock_runtime = boto3.client("bedrock-runtime", region_name=os.environ["REGION"])

def lambda_handler(event, context):
    input_text = event.get("input_text", "")
    trigger_ts = event.get("trigger_ts", "")

    try:
        prompt = f"""Create a professional team update email using EXACTLY these updates:

{input_text}

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

        response = bedrock_runtime.invoke_model(
            modelId="us.meta.llama3-2-11b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )

        response_body = json.loads(response['body'].read())
        summary = response_body.get("generation", str(response_body))

        # Validate tickets
        original_tickets = set(re.findall(r"#\w+", input_text))
        summary_tickets = set(re.findall(r"#\w+", summary))

        if not summary_tickets.issubset(original_tickets):
            return {
                "bedrockResult": "⚠️ Summary validation failed - unexpected ticket numbers detected",
                "trigger_ts": trigger_ts
            }

        return {
            "bedrockResult": summary.strip() if summary else "No summary could be generated.",
            "trigger_ts": trigger_ts
        }

    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        return {
            "bedrockResult": f"Error generating summary: {str(e)}",
            "trigger_ts": trigger_ts
        }
