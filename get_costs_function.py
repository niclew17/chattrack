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
        # Get the Authorization header
        headers = event.get('headers', {})
        if not headers or 'Authorization' not in headers:
            logger.error("No Authorization header present")
            return False

        auth_token = headers['Authorization'].replace('Bearer ', '')

        # Query the organization table using the auth token index
        response = org_table.query(
            IndexName='AuthTokenIndex',
            KeyConditionExpression='auth_token = :token',
            ExpressionAttributeValues={':token': auth_token}
        )

        # Check if we found a matching organization
        if not response['Items']:
            logger.error("No organization found for the provided auth token")
            return False

        # Verify the organization ID matches
        org = response['Items'][0]
        if org['organization_id'] != organization_id:
            logger.error("Organization ID mismatch")
            return False

        # Verify the organization is active
        if org.get('status') != 'active':
            logger.error("Organization is not active")
            return False

        return True

    except Exception as e:
        logger.error(f"Error during authorization: {str(e)}")
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