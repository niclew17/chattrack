"""Lambda function to delete an organization and its associated data."""

import os
import json
import boto3
from pythonjsonlogger import jsonlogger
import logging

# Configure logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
org_table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
usage_table = dynamodb.Table('chatgpt_usage_tracking')  # We'll need this to delete usage data

def validate_auth_token(auth_token, organization_id):
    """Validate the auth token belongs to the organization."""
    try:
        # Query the auth token index
        response = org_table.query(
            IndexName='AuthTokenIndex',
            KeyConditionExpression='auth_token = :token',
            ExpressionAttributeValues={':token': auth_token}
        )
        
        # Check if we found a matching organization
        if response['Items']:
            stored_org = response['Items'][0]
            if stored_org['organization_id'] == organization_id:
                return True, stored_org
            else:
                return False, "Auth token does not match organization ID"
        else:
            return False, "Invalid auth token"
            
    except Exception as e:
        logger.error(f"Error validating auth token: {str(e)}")
        return False, str(e)

def delete_organization_usage_data(organization_id):
    """Delete all usage data for the organization."""
    try:
        # Query all usage records for the organization
        response = usage_table.query(
            KeyConditionExpression='organization_id = :org_id',
            ExpressionAttributeValues={':org_id': organization_id}
        )
        
        # Delete each usage record
        with usage_table.batch_writer() as batch:
            for item in response['Items']:
                batch.delete_item(
                    Key={
                        'organization_id': item['organization_id'],
                        'record_id': item['record_id']
                    }
                )
        
        return True, None
    except Exception as e:
        logger.error(f"Error deleting usage data: {str(e)}")
        return False, str(e)

def lambda_handler(event, context):
    """Handle the deletion of an organization."""
    try:
        # Parse request
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing request body'})
            }
            
        body = json.loads(event['body'])
        
        # Validate required fields
        required_fields = ['organization_id', 'auth_token']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        organization_id = body['organization_id']
        auth_token = body['auth_token']
        
        # Validate auth token
        is_valid, auth_result = validate_auth_token(auth_token, organization_id)
        if not is_valid:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': f'Authentication failed: {auth_result}'})
            }
            
        # Delete usage data first
        success, error = delete_organization_usage_data(organization_id)
        if not success:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Failed to delete usage data: {error}'})
            }
            
        # Delete the organization record
        org_table.delete_item(
            Key={'organization_id': organization_id}
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Organization and associated data deleted successfully',
                'organization_id': organization_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error in delete_org_function: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 