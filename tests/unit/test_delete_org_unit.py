"""Unit tests for the delete organization function."""

import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch
import os
import sys

# Add lambda directory to path
lambda_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/lambda'))
sys.path.insert(0, lambda_dir)

from delete_org_function import lambda_handler

@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_TABLE'] = 'chatgpt_organizations'

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test."""
    with mock_aws():
        yield

@pytest.fixture
def dynamodb_tables():
    """Create mock DynamoDB tables."""
    dynamodb = boto3.resource('dynamodb')
    
    # Delete tables if they exist
    try:
        dynamodb.Table('chatgpt_organizations').delete()
    except:
        pass
    try:
        dynamodb.Table('chatgpt_usage_tracking').delete()
    except:
        pass
    
    # Create the organizations table
    org_table = dynamodb.create_table(
        TableName='chatgpt_organizations',
        KeySchema=[{'AttributeName': 'organization_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'organization_id', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )

    # Create the usage tracking table
    usage_table = dynamodb.create_table(
        TableName='chatgpt_usage_tracking',
        KeySchema=[
            {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
            {'AttributeName': 'record_id', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'organization_id', 'AttributeType': 'S'},
            {'AttributeName': 'record_id', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )

    # Wait for tables to be ready
    org_table.meta.client.get_waiter('table_exists').wait(TableName='chatgpt_organizations')
    usage_table.meta.client.get_waiter('table_exists').wait(TableName='chatgpt_usage_tracking')

    # Add test data
    org_table.put_item(Item={
        'organization_id': 'test-org',
        'auth_token': 'valid-token',
        'name': 'Test Organization'
    })

    usage_table.put_item(Item={
        'organization_id': 'test-org',
        'record_id': 'test-record',
        'usage_data': 'test data'
    })

    yield dynamodb

@patch('delete_org_function.validate_auth_token')
def test_delete_organization_success(mock_validate_auth, dynamodb_tables):
    """Test successful organization deletion."""
    # Mock successful auth validation
    mock_validate_auth.return_value = (True, {'organization_id': 'test-org'})
    
    # Ensure the organization exists
    dynamodb = boto3.resource('dynamodb')
    org_table = dynamodb.Table('chatgpt_organizations')
    org_table.put_item(Item={
        'organization_id': 'test-org',
        'auth_token': 'valid-token',
        'name': 'Test Organization'
    })
    
    event = {
        'body': json.dumps({
            'organization_id': 'test-org',
            'auth_token': 'valid-token'
        })
    }
    
    response = lambda_handler(event, {})
    
    assert response['statusCode'] == 200
    assert 'Organization and associated data deleted successfully' in response['body']
    
    # Verify organization was deleted
    response = org_table.get_item(Key={'organization_id': 'test-org'})
    assert 'Item' not in response

@patch('delete_org_function.validate_auth_token')
def test_delete_organization_invalid_auth(mock_validate_auth, dynamodb_tables):
    """Test deletion with invalid auth token."""
    # Mock failed auth validation
    mock_validate_auth.return_value = (False, "Invalid auth token")
    
    # Ensure the organization exists
    dynamodb = boto3.resource('dynamodb')
    org_table = dynamodb.Table('chatgpt_organizations')
    org_table.put_item(Item={
        'organization_id': 'test-org',
        'auth_token': 'valid-token',
        'name': 'Test Organization'
    })
    
    event = {
        'body': json.dumps({
            'organization_id': 'test-org',
            'auth_token': 'invalid-token'
        })
    }
    
    response = lambda_handler(event, {})
    assert response['statusCode'] == 401
    assert 'Authentication failed' in response['body']
    
    # Verify organization was not deleted
    response = org_table.get_item(Key={'organization_id': 'test-org'})
    assert 'Item' in response

def test_delete_organization_missing_fields(dynamodb_tables):
    """Test deletion with missing required fields."""
    event = {
        'body': json.dumps({})
    }
    
    response = lambda_handler(event, {})
    assert response['statusCode'] == 400
    assert 'Missing required field: organization_id' in response['body'] 