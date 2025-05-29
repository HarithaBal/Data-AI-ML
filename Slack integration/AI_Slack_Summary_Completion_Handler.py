import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Step Function execution completed.")
    logger.info(f"Final input payload: {json.dumps(event)}")
    
    # Optional: Notify or log to external system, e.g., CloudWatch, Slack, etc.
    # post_to_slack("Summary and email successfully sent.")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Step Function execution completed successfully.",
            "input": event
        })
    }
