import json
import pytest
from moto import mock_dynamodb
import boto3
from lambda_function import lambda_handler

@pytest.fixture
def dynamodb_table():
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb')
        
        # Create the table
        table = dynamodb.create_table(
            TableName='chatgpt_usage_tracking',
            KeySchema=[
                {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
                {'AttributeName': 'user_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'organization_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'OrgTimestampIndex',
                    'KeySchema': [
                        {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'UserTimestampIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table

def test_lambda_handler_success(dynamodb_table):
    # Test event
    event = {
        'body': json.dumps({
            'model_name': 'gpt-4',
            'input_tokens': 100,
            'output_tokens': 50,
            'user_id': 'test_user',
            'organization_id': 'test_org'
        })
    }
    
    # Call the handler
    response = lambda_handler(event, {})
    
    # Assert response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Usage data recorded successfully'
    assert body['organization_id'] == 'test_org'
    assert body['user_id'] == 'test_user'
    assert 'total_cost' in body
    assert 'timestamp' in body

def test_lambda_handler_missing_field():
    # Test event missing required field
    event = {
        'body': json.dumps({
            'model_name': 'gpt-4',
            'input_tokens': 100,
            # missing output_tokens
            'user_id': 'test_user',
            'organization_id': 'test_org'
        })
    }
    
    # Call the handler
    response = lambda_handler(event, {})
    
    # Assert response
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Missing required field' in body['error']

def test_lambda_handler_invalid_model():
    # Test event with invalid model
    event = {
        'body': json.dumps({
            'model_name': 'invalid-model',
            'input_tokens': 100,
            'output_tokens': 50,
            'user_id': 'test_user',
            'organization_id': 'test_org'
        })
    }
    
    # Call the handler
    response = lambda_handler(event, {})
    
    # Assert response
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Unsupported model' in body['error'] 