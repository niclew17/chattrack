import json
import boto3
import uuid
import os
from datetime import datetime, timezone
import logging
from decimal import Decimal

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=region)
table_name = os.environ.get('DYNAMODB_TABLE', 'chatgpt_usage_tracking')
org_table_name = os.environ.get('ORG_TABLE_NAME', 'chatgpt_organizations')
table = dynamodb.Table(table_name)
org_table = dynamodb.Table(org_table_name)

def authorize_request(event, organization_id):
    """
    Validate the auth token against the organization ID.
    Returns True if authorized, False otherwise.
    """
    try:
        # Log the full event for debugging
        logger.info(f"Full event: {json.dumps(event)}")
        
        # Get the Authorization header
        headers = event.get('headers', {})
        logger.info(f"Headers received: {json.dumps(headers)}")
        
        if not headers:
            logger.error("No headers present")
            return False

        # Handle different possible header key formats
        auth_header = None
        for key in headers:
            if key.lower() == 'authorization' or key.lower() == '"authorization"':
                auth_header = headers[key]
                break

        if not auth_header:
            logger.error("No Authorization header present")
            return False

        # Clean up the auth token - remove quotes and extra spaces
        auth_token = auth_header.replace('"', '').strip()
        if auth_token.lower().startswith('bearer '):
            auth_token = auth_token[7:].strip()

        logger.info(f"Cleaned auth token: {auth_token}")
        logger.info(f"Organization table name: {org_table_name}")

        # Query the organization table using the auth token index
        try:
            response = org_table.query(
                IndexName='AuthTokenIndex',
                KeyConditionExpression='auth_token = :token',
                ExpressionAttributeValues={':token': auth_token}
            )
            logger.info(f"DynamoDB query response: {json.dumps(response)}")
        except Exception as e:
            logger.error(f"DynamoDB query error: {str(e)}")
            return False

        # Check if we found a matching organization
        if not response.get('Items'):
            logger.error("No organization found for the provided auth token")
            return False

        # Verify the organization ID matches
        org = response['Items'][0]
        logger.info(f"Found organization: {json.dumps(org)}")
        
        if org.get('organization_id') != organization_id:
            logger.error(f"Organization ID mismatch. Expected: {organization_id}, Found: {org.get('organization_id')}")
            return False

        # Verify the organization is active
        if org.get('status') != 'active':
            logger.error("Organization is not active")
            return False

        logger.info("Authorization successful")
        return True

    except Exception as e:
        logger.error(f"Error during authorization: {str(e)}")
        logger.error(f"Full error details: {str(e.__dict__)}")
        return False

# Simplified function that always returns True (no rate limiting)
def check_rate_limits(organization_id):
    # Rate limiting removed
    return True

def lambda_handler(event, context):
    try:
        # Parse the incoming JSON body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        # Validate required fields
        required_fields = ['model_name', 'input_tokens', 'output_tokens', 'user_id', 'organization_id']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Missing required field: {field}'
                    })
                }
        
        # Extract data from the request
        model_name = body['model_name']
        input_tokens = int(body['input_tokens'])
        output_tokens = int(body['output_tokens'])
        user_id = body['user_id']
        organization_id = body['organization_id']
        
        # Optional token counts
        cached_input_tokens = int(body.get('cached_input_tokens', 0))
        reasoning_tokens = int(body.get('reasoning_tokens', 0))
        
        # Authorize the request - ensure organization can only access their own data
        if not authorize_request(event, organization_id):
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Unauthorized access. Organizations can only access their own data.'
                })
            }
        
        # Calculate cost based on model and token usage
        # Pricing rates per 1,000,000 tokens (in USD) - update these as needed
        model_pricing = {
            # GPT-4 models
            'gpt-4': {'input': Decimal('30.0'), 'output': Decimal('60.0')},
            'gpt-4-32k': {'input': Decimal('60.0'), 'output': Decimal('120.0')},
            'gpt-4-turbo': {'input': Decimal('10.0'), 'output': Decimal('30.0'), 'cached_input': Decimal('1.5')},
            'gpt-4-turbo-preview': {'input': Decimal('10.0'), 'output': Decimal('30.0'), 'cached_input': Decimal('1.5')},
            'gpt-4-vision-preview': {'input': Decimal('10.0'), 'output': Decimal('30.0')},
            'gpt-4-1106-preview': {'input': Decimal('10.0'), 'output': Decimal('30.0'), 'cached_input': Decimal('1.5')},
            'gpt-4-0125-preview': {'input': Decimal('10.0'), 'output': Decimal('30.0'), 'cached_input': Decimal('1.5')},
            'gpt-4o': {'input': Decimal('5.0'), 'output': Decimal('15.0'), 'cached_input': Decimal('0.75')},
            'gpt-4o-2024-05-13': {'input': Decimal('5.0'), 'output': Decimal('15.0'), 'cached_input': Decimal('0.75')},
            
            # GPT-3.5 models
            'gpt-3.5-turbo': {'input': Decimal('1.5'), 'output': Decimal('2.0'), 'cached_input': Decimal('0.3')},
            'gpt-3.5-turbo-16k': {'input': Decimal('3.0'), 'output': Decimal('4.0'), 'cached_input': Decimal('0.6')},
            'gpt-3.5-turbo-instruct': {'input': Decimal('1.5'), 'output': Decimal('2.0')},
            'gpt-3.5-turbo-0125': {'input': Decimal('0.5'), 'output': Decimal('1.5'), 'cached_input': Decimal('0.1')},
            'gpt-3.5-turbo-0613': {'input': Decimal('1.5'), 'output': Decimal('2.0'), 'cached_input': Decimal('0.3')},
            'gpt-3.5-turbo-1106': {'input': Decimal('1.0'), 'output': Decimal('2.0'), 'cached_input': Decimal('0.2')},
            
            # Claude models
            'claude-3-opus-20240229': {'input': Decimal('15.0'), 'output': Decimal('75.0')},
            'claude-3-sonnet-20240229': {'input': Decimal('3.0'), 'output': Decimal('15.0')},
            'claude-3-haiku-20240307': {'input': Decimal('0.25'), 'output': Decimal('1.25')},
            'claude-2.1': {'input': Decimal('8.0'), 'output': Decimal('24.0')},
            'claude-2.0': {'input': Decimal('8.0'), 'output': Decimal('24.0')},
            'claude-instant-1.2': {'input': Decimal('0.8'), 'output': Decimal('2.4')},
            
            # Mistral models
            'mistral-tiny': {'input': Decimal('0.14'), 'output': Decimal('0.42')},
            'mistral-small': {'input': Decimal('0.6'), 'output': Decimal('1.8')},
            'mistral-medium': {'input': Decimal('2.7'), 'output': Decimal('8.1'), 'reasoning': Decimal('0.9')},
            'mistral-large': {'input': Decimal('8.0'), 'output': Decimal('24.0'), 'reasoning': Decimal('2.7')},
            
            # Llama models
            'llama-2-7b': {'input': Decimal('0.2'), 'output': Decimal('0.2')},
            'llama-2-13b': {'input': Decimal('0.3'), 'output': Decimal('0.4')},
            'llama-2-70b': {'input': Decimal('0.8'), 'output': Decimal('0.9')},
            'llama-3-8b': {'input': Decimal('0.3'), 'output': Decimal('0.3')},
            'llama-3-70b': {'input': Decimal('0.9'), 'output': Decimal('0.9')}
        }
        
        # Check if the model is supported
        if model_name not in model_pricing:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unsupported model: {model_name}. Supported models are: {", ".join(model_pricing.keys())}'
                })
            }
        
        # Get pricing for the model
        model_rates = model_pricing[model_name]
        
        # Calculate costs
        input_cost = (Decimal(str(input_tokens)) / Decimal('1000000')) * model_rates['input']
        output_cost = (Decimal(str(output_tokens)) / Decimal('1000000')) * model_rates['output']
        
        # Calculate cached input cost if applicable
        cached_input_cost = Decimal('0')
        if cached_input_tokens > 0 and 'cached_input' in model_rates:
            cached_input_cost = (Decimal(str(cached_input_tokens)) / Decimal('1000000')) * model_rates['cached_input']
            
        # Calculate reasoning tokens cost if applicable
        reasoning_cost = Decimal('0')
        if reasoning_tokens > 0 and 'reasoning' in model_rates:
            reasoning_cost = (Decimal(str(reasoning_tokens)) / Decimal('1000000')) * model_rates['reasoning']
            
        total_cost = input_cost + output_cost + cached_input_cost + reasoning_cost
        
        # Generate timestamp if not provided
        timestamp = body.get('timestamp', datetime.now(timezone.utc).isoformat())
        
        # Generate a unique record ID
        record_id = str(uuid.uuid4())
        
        # Create item to store in DynamoDB with organization and record_id as keys
        item = {
            'organization_id': organization_id,  # Partition key
            'record_id': record_id,             # Sort key
            'user_id': user_id,                 # For GSI
            'timestamp': timestamp,             # For GSI and time-based queries
            'total_cost': total_cost
        }
        
        # Add any additional fields from the request
        for key, value in body.items():
            # Skip fields we've already processed or don't want to store
            if key not in item and key not in ['model_name', 'input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens']:
                item[key] = value
        
        # Store the data in DynamoDB
        table.put_item(Item=item)
        
        # Log the usage
        logger.info({
            'action': 'usage_tracking',
            'organization_id': organization_id,
            'user_id': user_id,
            'total_cost': str(total_cost),  # Convert to string for logging to preserve precision
            'timestamp': timestamp
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Usage data recorded successfully',
                'organization_id': organization_id,
                'user_id': user_id,
                'total_cost': float(total_cost)  # Convert to float for JSON serialization
            }, default=str)  # Use default=str to handle Decimal serialization
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 