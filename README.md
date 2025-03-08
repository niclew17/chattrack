# ChatGPT API Usage Tracker

This AWS Lambda function provides a public API for organizations to track their customers' AI model usage costs. Organizations can use their own identifiers and track usage for their customers without complex authentication setup.

## Key Features

- **Self-Service Organization Management**: Organizations can use their own identifiers
- **Per-Customer Usage Tracking**: Track API usage costs for each of your customers
- **Minimal Data Storage**: Only stores essential information (organization ID, user ID, timestamp, cost)
- **Simple Deployment**: Easy to deploy without complex encryption or authentication setup
- **Optimized Queries**: Efficient database structure for analyzing usage patterns

## Setup Instructions

### 1. Create a DynamoDB Table

Create a DynamoDB table with the following configuration:
- Table name: `chatgpt_usage_tracking` (or customize and set as environment variable)
- Partition key: `organization_id` (String)
- Sort key: `user_id` (String)
- Global Secondary Indexes:
  - Name: `OrgTimestampIndex`
    - Partition key: `organization_id` (String)
    - Sort key: `timestamp` (String)
  - Name: `UserTimestampIndex`
    - Partition key: `user_id` (String)
    - Sort key: `timestamp` (String)

### 2. Deploy the Lambda Function

1. Create a new Lambda function in AWS:
   - Runtime: Python 3.9+
   - Handler: lambda_function.lambda_handler
   - Architecture: x86_64 or arm64

2. Set up environment variables:
   - `DYNAMODB_TABLE`: Name of your DynamoDB table (default: `chatgpt_usage_tracking`)

3. Configure IAM permissions:
   - DynamoDB access permissions for your table

4. Deploy the code:
   - Zip the `lambda_function.py` file
   - Upload to AWS Lambda

### 3. Configure API Gateway

1. Create a new REST API in API Gateway
2. Create a resource and add a POST method
3. Set the integration type to Lambda Function
4. Configure CORS if needed
5. Deploy the API

### 4. Simplified Deployment with AWS SAM

For easier deployment, use the provided template.yaml with AWS SAM:

```bash
# Install AWS SAM CLI if you haven't already
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html

# Package and deploy
sam build
sam deploy --guided
```

## Integration Guide

### When to Call This API

Call this API immediately after each AI model request to track usage:

1. Your application makes a request to an AI model API (OpenAI, Anthropic, etc.)
2. You receive the response with token usage information
3. Call this tracking API to log the usage for that customer

### Example Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Your Customer  │────▶│  Your API/App   │────▶│   AI Model API  │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └────────┬────────┘
                                 │                       │
                                 │                       │
                                 │                       ▼
                                 │              ┌─────────────────┐
                                 │              │                 │
                                 │              │    Response     │
                                 │              │  w/ token info  │
                                 │              │                 │
                                 │              └────────┬────────┘
                                 │                       │
                                 ▼                       │
                        ┌─────────────────┐             │
                        │                 │             │
                        │  Usage Tracker  │◀────────────┘
                        │      API        │
                        │                 │
                        └─────────────────┘
```

## Usage

### 1. Track Usage (POST /track)

Send a POST request to your API Gateway endpoint with the following JSON body:

```json
{
  "organization_id": "org_12345",
  "model_name": "gpt-4",
  "input_tokens": 150,
  "output_tokens": 50,
  "user_id": "customer_6789"
}
```

### 2. Get Usage Costs (GET /costs)

Send a GET request to your API Gateway endpoint with the following query parameters:

Required Parameters:
- `organization_id`: Your organization's unique identifier
- `user_id`: Unique identifier for your customer
- `start_date`: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- `end_date`: End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

Example Request:
```
GET /costs?organization_id=org_12345&user_id=customer_6789&start_date=2024-03-01&end_date=2024-03-31
```

Successful Response:
```json
{
  "organization_id": "org_12345",
  "user_id": "customer_6789",
  "start_date": "2024-03-01T00:00:00",
  "end_date": "2024-03-31T23:59:59",
  "total_cost": 12.45,
  "usage_count": 150,
  "time_period_days": 31
}
```

The response includes:
- `total_cost`: Sum of all costs for the specified period
- `usage_count`: Number of API calls made during the period
- `time_period_days`: Number of days between start_date and end_date

## Data Storage

The service only stores the following information in DynamoDB:
- `organization_id`: Your organization's identifier
- `user_id`: Your customer's identifier
- `timestamp`: When the request was made
- `total_cost`: The calculated cost of the API usage

All other fields (model_name, token counts, etc.) are used for cost calculation but not stored in the database.

## Error Handling

The Lambda function handles various error cases:
- Missing required fields (400 Bad Request)
- Internal server errors (500 Internal Server Error)