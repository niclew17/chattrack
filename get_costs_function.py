import json
import boto3
import os
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import logging

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

def lambda_handler(event, context):
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters', {})
        if not query_params:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing query parameters'
                })
            }

        # Extract and validate required parameters
        required_params = ['user_id', 'organization_id', 'start_date', 'end_date']
        for param in required_params:
            if param not in query_params:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Missing required parameter: {param}'
                    })
                }

        organization_id = query_params['organization_id']
        user_id = query_params['user_id']
        start_date = query_params['start_date']
        end_date = query_params['end_date']

        # Authorize the request
        if not authorize_request(event, organization_id):
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'Unauthorized access'
                })
            }

        # Query DynamoDB for usage data
        response = table.query(
            IndexName='UserTimestampIndex',
            KeyConditionExpression='user_id = :uid AND #ts BETWEEN :start AND :end',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={
                ':uid': user_id,
                ':start': start_date,
                ':end': end_date
            }
        )

        # Calculate total cost
        total_cost = sum(float(item['total_cost']) for item in response['Items'])
        usage_count = len(response['Items'])

        return {
            'statusCode': 200,
            'body': json.dumps({
                'organization_id': organization_id,
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_cost': total_cost,
                'usage_count': usage_count
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