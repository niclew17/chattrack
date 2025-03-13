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
        # Parse the incoming query parameters
        if 'queryStringParameters' not in event or not event['queryStringParameters']:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing query parameters'
                })
            }
        
        params = event['queryStringParameters']
        
        # Validate required parameters
        required_params = ['organization_id', 'start_date', 'end_date']
        for param in required_params:
            if param not in params:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': f'Missing required parameter: {param}'
                    })
                }
        
        # Extract parameters
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
        
        # Query DynamoDB using the OrgTimestampIndex
        response = table.query(
            IndexName='OrgTimestampIndex',
            KeyConditionExpression=
                Key('organization_id').eq(organization_id) & 
                Key('timestamp').between(start_date, end_date)
        )
        
        # Process results by user
        user_costs = {}
        total_org_cost = Decimal('0')
        
        for item in response['Items']:
            user_id = item['user_id']
            cost = Decimal(str(item['total_cost']))
            
            # Initialize user data if not exists
            if user_id not in user_costs:
                user_costs[user_id] = {
                    'total_cost': Decimal('0'),
                    'usage_count': 0
                }
            
            # Update user statistics
            user_costs[user_id]['total_cost'] += cost
            user_costs[user_id]['usage_count'] += 1
            total_org_cost += cost
        
        # Convert user costs to list and sort by total cost (highest first)
        user_costs_list = [
            {
                'user_id': user_id,
                'total_cost': float(data['total_cost']),  # Convert Decimal to float for JSON
                'usage_count': data['usage_count']
            }
            for user_id, data in user_costs.items()
        ]
        user_costs_list.sort(key=lambda x: x['total_cost'], reverse=True)
        
        # Prepare the response
        result = {
            'organization_id': organization_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_organization_cost': float(total_org_cost),  # Convert Decimal to float for JSON
            'total_users': len(user_costs),
            'time_period_days': (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days,
            'user_costs': user_costs_list
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