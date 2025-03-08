# ChatGPT API Usage Tracker

This AWS Lambda function enables organizations to track their customers' AI model usage costs. It provides a secure, multi-tenant system where each organization can only access their own customers' data.

## Key Features

- **Strict Organization Isolation**: Each organization can only access data from their own customers
- **Per-Customer Usage Tracking**: Track API usage costs for each of your customers
- **Minimal Data Storage**: Only stores essential information (organization ID, user ID, timestamp, cost)
- **Secure Encryption**: Organization-specific encryption keys ensure data privacy
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

### 2. Set Up KMS Encryption Keys

Create organization-specific KMS keys:
- Create a KMS key for each organization with alias pattern: `alias/org-{organization_id}-key`
- Grant the Lambda function permission to use these keys

### 3. Deploy the Lambda Function

1. Create a new Lambda function in AWS:
   - Runtime: Python 3.9+
   - Handler: lambda_function.lambda_handler
   - Architecture: x86_64 or arm64

2. Set up environment variables:
   - `DYNAMODB_TABLE`: Name of your DynamoDB table (default: `chatgpt_usage_tracking`)

3. Configure IAM permissions:
   - DynamoDB access permissions
   - KMS key usage permissions

4. Deploy the code:
   - Zip the `lambda_function.py` and dependencies
   - Upload to AWS Lambda

### 4. Configure API Gateway with Authentication

1. Create a new REST API in API Gateway
2. Set up Cognito or custom authorizer to validate organization identity
3. Create a resource and add a POST method
4. Set the integration type to Lambda Function
5. Configure CORS if needed
6. Deploy the API

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

### Required Fields

- `organization_id`: Your organization's unique identifier
- `model_name`: Name of the AI model used (e.g., "gpt-3.5-turbo", "gpt-4")
- `input_tokens`: Number of input tokens used
- `output_tokens`: Number of output tokens generated
- `user_id`: Unique identifier for your customer

### Optional Fields

- `timestamp`: ISO format timestamp (auto-generated if not provided)
- `cached_input_tokens`: Number of cached input tokens (for models that support caching)
- `reasoning_tokens`: Number of reasoning tokens (for models that support reasoning)

### Data Storage

The service only stores the following information in DynamoDB:
- `organization_id`: Your organization's identifier
- `user_id`: Your customer's identifier
- `timestamp`: When the request was made
- `total_cost`: The calculated cost of the API usage

All other fields (model_name, token counts, etc.) are used for cost calculation but not stored in the database.

## Common Query Patterns

### 1. Get Usage for a Specific Customer

Query the primary table using organization_id and user_id:

```
organization_id = "org_12345" AND user_id = "customer_6789"
```

### 2. Get All Customer Usage for an Organization

Query the primary table using just the organization_id:

```
organization_id = "org_12345"
```

### 3. Get Usage by Time Period for an Organization

Query the OrgTimestampIndex:

```
organization_id = "org_12345" AND timestamp BETWEEN "2023-01-01" AND "2023-01-31"
```

### 4. Get Usage History for a Specific Customer

Query the UserTimestampIndex:

```
user_id = "customer_6789" AND timestamp BETWEEN "2023-01-01" AND "2023-01-31"
```

## Response

Successful response:
```json
{
  "message": "Usage data recorded successfully",
  "organization_id": "org_12345",
  "user_id": "customer_6789",
  "total_cost": 0.00875
}
```

## Error Handling

The Lambda function handles various error cases:
- Missing required fields (400 Bad Request)
- Unauthorized access (403 Forbidden)
- Rate limiting (429 Too Many Requests)
- Internal server errors (500 Internal Server Error) 