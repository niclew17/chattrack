import json
import boto3
import os
import uuid
import logging
from datetime import datetime, timezone

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=region)
table_name = os.environ.get('DYNAMODB_TABLE', 'chatgpt_organizations')
table = dynamodb.Table(table_name)

def generate_auth_token():
    """Generate a unique auth token for the organization."""
    return str(uuid.uuid4())

def lambda_handler(event, context):
    try:
        # Parse the incoming JSON body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event

        # Validate required fields
        if 'organization_name' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: organization_name'
                })
            }

        # Generate organization ID and auth token
        organization_id = f"org_{str(uuid.uuid4())}"
        auth_token = generate_auth_token()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create item to store in DynamoDB
        item = {
            'organization_id': organization_id,
            'organization_name': body['organization_name'],
            'auth_token': auth_token,
            'created_at': timestamp,
            'status': 'active'
        }

        # Store optional fields if provided
        optional_fields = ['contact_email', 'description']
        for field in optional_fields:
            if field in body:
                item[field] = body[field]

        # Store the organization data in DynamoDB
        table.put_item(Item=item)

        # Log the registration
        logger.info({
            'action': 'organization_registration',
            'organization_id': organization_id,
            'organization_name': body['organization_name'],
            'timestamp': timestamp
        })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Organization registered successfully',
                'organization_id': organization_id,
                'auth_token': auth_token,
                'organization_name': body['organization_name']
            })
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 