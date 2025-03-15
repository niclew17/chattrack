# ChatGPT Usage Tracking API

API for tracking and retrieving ChatGPT usage costs.

## Endpoints

### Track Usage (POST /track)

Records ChatGPT API usage data.

```http
POST /track
Content-Type: application/json

{
    "model_name": "gpt-4",
    "input_tokens": 100,
    "output_tokens": 50,
    "user_id": "user_123",
    "organization_id": "org_456"
}
```

### Get Costs (GET /costs)

Retrieves usage costs with optional filters.

```http
GET /costs?user_id=user_456&organization_id=org_123&start_date=2025-03-07&end_date=2025-03-09
```

For full documentation, see the [API Documentation](docs/API.md).

## API Endpoints

### 1. Track Usage (`POST /track`)

Records usage data for ChatGPT API calls.

#### Request

```http
POST /track
Content-Type: application/json

{
    "model_name": "gpt-4",
    "input_tokens": 100,
    "output_tokens": 50,
    "user_id": "user_123",
    "organization_id": "org_456",
    "cached_input_tokens": 20,     // Optional
    "reasoning_tokens": 30         // Optional
}
```

#### Supported Models and Pricing (per 1M tokens)

##### GPT-4 Models

- `gpt-4`: Input $30.00, Output $60.00
- `gpt-4-32k`: Input $60.00, Output $120.00
- `gpt-4-turbo`: Input $10.00, Output $30.00, Cached Input $1.50
- `gpt-4-turbo-preview`: Input $10.00, Output $30.00, Cached Input $1.50
- `gpt-4-vision-preview`: Input $10.00, Output $30.00
- `gpt-4-1106-preview`: Input $10.00, Output $30.00, Cached Input $1.50
- `gpt-4-0125-preview`: Input $10.00, Output $30.00, Cached Input $1.50
- `gpt-4o`: Input $5.00, Output $15.00, Cached Input $0.75
- `gpt-4o-2024-05-13`: Input $5.00, Output $15.00, Cached Input $0.75

##### GPT-3.5 Models

- `gpt-3.5-turbo`: Input $1.50, Output $2.00, Cached Input $0.30
- `gpt-3.5-turbo-16k`: Input $3.00, Output $4.00, Cached Input $0.60
- `gpt-3.5-turbo-instruct`: Input $1.50, Output $2.00
- `gpt-3.5-turbo-0125`: Input $0.50, Output $1.50, Cached Input $0.10
- `gpt-3.5-turbo-0613`: Input $1.50, Output $2.00, Cached Input $0.30
- `gpt-3.5-turbo-1106`: Input $1.00, Output $2.00, Cached Input $0.20

##### Claude Models

- `claude-3-opus-20240229`: Input $15.00, Output $75.00
- `claude-3-sonnet-20240229`: Input $3.00, Output $15.00
- `claude-3-haiku-20240307`: Input $0.25, Output $1.25
- `claude-2.1`: Input $8.00, Output $24.00
- `claude-2.0`: Input $8.00, Output $24.00
- `claude-instant-1.2`: Input $0.80, Output $2.40

##### Mistral Models

- `mistral-tiny`: Input $0.14, Output $0.42
- `mistral-small`: Input $0.60, Output $1.80
- `mistral-medium`: Input $2.70, Output $8.10, Reasoning $0.90
- `mistral-large`: Input $8.00, Output $24.00, Reasoning $2.70

##### Llama Models

- `llama-2-7b`: Input $0.20, Output $0.20
- `llama-2-13b`: Input $0.30, Output $0.40
- `llama-2-70b`: Input $0.80, Output $0.90
- `llama-3-8b`: Input $0.30, Output $0.30
- `llama-3-70b`: Input $0.90, Output $0.90

#### Success Response

```json
{
  "message": "Usage data recorded successfully",
  "organization_id": "org_456",
  "user_id": "user_123",
  "total_cost": 0.0045,
  "timestamp": "2024-03-08T15:30:00Z"
}
```

#### Error Responses

```json
// Invalid model
{
    "error": "Unsupported model: invalid-model. Supported models are: gpt-4, gpt-4-32k, ..."
}

// Missing field
{
    "error": "Missing required field: output_tokens"
}
```

### 2. Get Costs (`GET /costs`)

Retrieves usage costs for specified organizations, users, and date ranges.

#### Request

Query Parameters:

- `organization_id` (optional): Filter by organization
- `user_id` (optional): Filter by user
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format

#### Example Queries

1. Get costs for specific date range with all parameters:

```http
GET /costs?user_id=user_456&organization_id=org_123&start_date=2025-03-07&end_date=2025-03-09
```

2. Get all costs for an organization:

```http
GET /costs?organization_id=org_123
```

3. Get all costs for a user:

```http
GET /costs?user_id=user_456
```

#### Success Response

```json
{
  "total_cost": 1.25,
  "usage_data": [
    {
      "timestamp": "2024-03-08T15:30:00Z",
      "model_name": "gpt-4",
      "input_tokens": 100,
      "output_tokens": 50,
      "cost": 0.45
    }
  ],
  "organization_id": "org_123",
  "user_id": "user_456",
  "start_date": "2025-03-07",
  "end_date": "2025-03-09"
}
```

#### Error Response

```json
{
  "error": "Missing query parameters"
}
```

## Testing

You can test the API using the provided `test.py` script:

```bash
# Auto-discover endpoints from CloudFormation stack
python test.py

# Or specify endpoints manually
python test.py --track-endpoint "https://api.example.com/track" --costs-endpoint "https://api.example.com/costs"
```

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad Request (invalid input, missing fields)
- 403: Unauthorized
- 500: Internal Server Error

## Notes

1. All costs are calculated in USD
2. Timestamps are in ISO 8601 format
3. Token counts must be positive integers
4. Date ranges are inclusive
5. At least one of `organization_id` or `user_id` is required for cost queries
