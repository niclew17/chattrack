import json
import boto3
import uuid
import os
from datetime import datetime
from dynamodb_encryption_sdk.encrypted.table import EncryptedTable
from dynamodb_encryption_sdk.identifiers import CryptoAction
from dynamodb_encryption_sdk.material_providers.aws_kms_provider import AwsKmsCryptographicMaterialsProvider
from dynamodb_encryption_sdk.structures import AttributeActions
import logging

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'chatgpt_usage_tracking')
table = dynamodb.Table(table_name)

# Add authorization check
def authorize_request(event, organization_id):
    # Get the caller's identity from the request context
    # This assumes you're using API Gateway with IAM or Cognito authorization
    caller_context = event.get('requestContext', {}).get('authorizer', {})
    caller_org_id = caller_context.get('organization_id')
    
    # Organization can only access their own data
    # No super admin access - strict isolation between organizations
    return caller_org_id == organization_id

# Set up encryption with organization-specific keys
def get_encrypted_table(table_name, organization_id):
    table = dynamodb.Table(table_name)
    
    # Use organization-specific KMS key for strict isolation
    # Each organization gets their own encryption key
    kms_key_id = f"alias/org-{organization_id}-key" 
    
    aws_kms_cmp = AwsKmsCryptographicMaterialsProvider(key_id=kms_key_id)
    
    actions = AttributeActions(
        default_action=CryptoAction.ENCRYPT_AND_SIGN,
        attribute_actions={
            'organization_id': CryptoAction.SIGN_ONLY,  # Keep searchable
            'user_id': CryptoAction.SIGN_ONLY,          # Keep searchable
            'timestamp': CryptoAction.SIGN_ONLY          # Keep searchable for time-based queries
        }
    )
    
    encrypted_table = EncryptedTable(
        table=table,
        materials_provider=aws_kms_cmp,
        attribute_actions=actions
    )
    
    return encrypted_table

# Add comprehensive logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Check organization rate limits
def check_rate_limits(organization_id):
    # Implement rate limiting logic here
    # For example, using Redis or DynamoDB to track request counts
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
        
        # Calculate cost based on model and token usage
        # Pricing rates per 1,000,000 tokens (in USD) - update these as needed
        model_pricing = {
            # GPT-4 models
            
            'gpt-4.5-preview': {'input': 75.0, 'output': 150.0, 'cached_input': 37.5},
            'gpt-4o-2024-08-06': {'input': 2.5, 'output': 10.0, 'cached_input': 1.25},
            'gpt-4o-audio-preview-2024-12-17': {'input': 2.5, 'output': 10.0},
            'gpt-4o-realtime-preview-2024-12-17': {'input': 5.0, 'output': 20.0, 'cached_input': 2.5},
            'gpt-4o-mini-2024-07-18': {'input': 0.15, 'output': 0.60, 'cached_input': 0.075},
            'gpt-4o-mini-audio-preview-2024-12-17': {'input': 0.15, 'output': 0.60},
            'gpt-4o-mini-realtime-preview-2024-12-17': {'input': 0.60, 'output': 2.40, 'cached_input': 0.30},
            'o1-2024-12-17': {'input': 15.0, 'output': 60.0, 'cached_input': 7.5},
            'o3-mini-2025-01-31': {'input': 1.10, 'output': 4.40, 'cached_input': 0.55},
            'o1-mini-2024-09-12': {'input': 1.10, 'output': 4.40, 'cached_input': 0.55},

            
            # GPT-3.5 models
            'gpt-3.5-turbo': {'input': 1.5, 'output': 2.0, 'cached_input': 0.3},
            'gpt-3.5-turbo-16k': {'input': 3.0, 'output': 4.0, 'cached_input': 0.6},
            'gpt-3.5-turbo-instruct': {'input': 1.5, 'output': 2.0},
            'gpt-3.5-turbo-0125': {'input': 0.5, 'output': 1.5, 'cached_input': 0.1},
            'gpt-3.5-turbo-0613': {'input': 1.5, 'output': 2.0, 'cached_input': 0.3},
            'gpt-3.5-turbo-1106': {'input': 1.0, 'output': 2.0, 'cached_input': 0.2},
            
            # Claude models
            'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0},
            'claude-3-sonnet-20240229': {'input': 3.0, 'output': 15.0},
            'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},
            'claude-2.1': {'input': 8.0, 'output': 24.0},
            'claude-2.0': {'input': 8.0, 'output': 24.0},
            'claude-instant-1.2': {'input': 0.8, 'output': 2.4},
            
            # Mistral models
            'mistral-tiny': {'input': 0.14, 'output': 0.42},
            'mistral-small': {'input': 0.6, 'output': 1.8},
            'mistral-medium': {'input': 2.7, 'output': 8.1, 'reasoning': 0.9},
            'mistral-large': {'input': 8.0, 'output': 24.0, 'reasoning': 2.7},
            
            # Llama models
            'llama-2-7b': {'input': 0.2, 'output': 0.2},
            'llama-2-13b': {'input': 0.3, 'output': 0.4},
            'llama-2-70b': {'input': 0.8, 'output': 0.9},
            'llama-3-8b': {'input': 0.3, 'output': 0.3},
            'llama-3-70b': {'input': 0.9, 'output': 0.9}
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
        input_cost = (input_tokens / 1000000) * model_rates['input']
        output_cost = (output_tokens / 1000000) * model_rates['output']
        
        # Calculate cached input cost if applicable
        cached_input_cost = 0
        if cached_input_tokens > 0 and 'cached_input' in model_rates:
            cached_input_cost = (cached_input_tokens / 1000000) * model_rates['cached_input']
            
        # Calculate reasoning tokens cost if applicable
        reasoning_cost = 0
        if reasoning_tokens > 0 and 'reasoning' in model_rates:
            reasoning_cost = (reasoning_tokens / 1000000) * model_rates['reasoning']
            
        total_cost = input_cost + output_cost + cached_input_cost + reasoning_cost
        
        # Generate timestamp if not provided
        timestamp = body.get('timestamp', datetime.now(datetime.UTC).isoformat())
        
        # Authorize the request - ensure organization can only access their own data
        if not authorize_request(event, organization_id):
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Unauthorized access. Organizations can only access their own data.'
                })
            }
        
        # Check rate limits for the organization
        if not check_rate_limits(organization_id):
            return {
                'statusCode': 429,
                'body': json.dumps({
                    'error': 'Rate limit exceeded for organization'
                })
            }
        
        # Create item to store in DynamoDB with organization and user as composite key
        item = {
            'organization_id': organization_id,  # Partition key
            'user_id': user_id,                  # Sort key
            'timestamp': timestamp,              # For time-based queries
            'total_cost': total_cost
        }
        
        # Add any additional fields from the request
        for key, value in body.items():
            # Skip fields we've already processed or don't want to store
            if key not in item and key not in ['request_id', 'conversation_id', 'model_name', 'input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens']:
                item[key] = value
        
        # Use encryption
        encrypted_table = get_encrypted_table(table_name, organization_id)
        encrypted_table.put_item(Item=item)
        
        # Add comprehensive logging
        logger.info({
            'action': 'usage_tracking',
            'organization_id': organization_id,
            'user_id': user_id,
            'total_cost': total_cost,
            'timestamp': timestamp
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Usage data recorded successfully',
                'organization_id': organization_id,
                'user_id': user_id,
                'total_cost': total_cost
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 