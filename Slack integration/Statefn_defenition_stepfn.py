{
  "Comment": "Weekly update workflow",
  "StartAt": "WaitForUserUpdates",
  "States": {
    "WaitForUserUpdates": {
      "Type": "Wait",
      "Seconds": 120,
      "Next": "Fetch_userinfo"
    },
    "Fetch_userinfo": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:519852036875:function:AI_Slacksummarizer_Fetch_userinfo",
      "Next": "Invoking Bedrock Model"
    },
    "Invoking Bedrock Model": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:519852036875:function:AI_Slacksummarizer_Bedrock_Summary",
      "Next": "FanOut"
    },
    "FanOut": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "PostToSlack",
          "States": {
            "PostToSlack": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-2:519852036875:function:AI_Slacksummarizer_Post_Back_to_Slack",
              "Parameters": {
                "summary.$": "$.bedrockResult",
                "trigger_ts.$": "$.trigger_ts"
              },
              "End": true
            }
          }
        },
        {
          "StartAt": "SendEmail",
          "States": {
            "SendEmail": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-2:519852036875:function:AI_Slack_Summary_SES_Email",
              "Parameters": {
                "bedrockResult.$": "$.bedrockResult",
                "trigger_ts.$": "$.trigger_ts"
              },
              "End": true
            }
          }
        }
      ],
      "Next": "Wait"
    },
    "Wait": {
      "Type": "Wait",
      "Seconds": 40,
      "Next": "FinalCleanup"
    },
    "FinalCleanup": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:519852036875:function:AI_Slack_Summary_Completion_Handler",
      "End": true
    }
  }
}