import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize logging
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'chatgpt_usage_tracking')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Parse the incoming JSON body
        if 'queryStringParameters' not in event or not event['queryStringParameters']:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing query parameters'
                })
            }
        
        params = event['queryStringParameters']
        
        # Validate required parameters
        required_params = ['user_id', 'organization_id', 'start_date', 'end_date']
        for param in required_params:
            if param not in params:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Missing required parameter: {param}'
                    })
                }
        
        # Extract parameters
        user_id = params['user_id']
        organization_id = params['organization_id']
        start_date = params['start_date']
        end_date = params['end_date']
        
        # Validate date formats
        try:
            # Convert to ISO format if not already
            start_date = datetime.fromisoformat(start_date).isoformat()
            end_date = datetime.fromisoformat(end_date).isoformat()
        except ValueError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid date format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'
                })
            }
        
        # Query DynamoDB using the GSI for better performance
        response = table.query(
            IndexName='OrgTimestampIndex',
            KeyConditionExpression=
                Key('organization_id').eq(organization_id) & 
                Key('timestamp').between(start_date, end_date),
            FilterExpression=
                Attr('user_id').eq(user_id)
        )
        
        # Calculate total cost
        total_cost = sum(Decimal(str(item['total_cost'])) for item in response['Items'])
        
        # Get usage counts
        usage_count = len(response['Items'])
        
        # Prepare the response
        result = {
            'organization_id': organization_id,
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_cost': float(total_cost),  # Convert Decimal to float for JSON serialization
            'usage_count': usage_count,
            'time_period_days': (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 