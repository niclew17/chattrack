"""Unit tests for the delete organization function."""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '../../src/lambda')
from delete_org_function import lambda_handler, validate_auth_token, delete_organization_usage_data

@pytest.fixture
def valid_event():
    """Create a valid API Gateway event."""
    return {
        'body': json.dumps({
            'organization_id': 'test-org-123',
            'auth_token': 'test-token-456'
        })
    }

@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource and tables."""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table

def test_validate_auth_token_success(mock_dynamodb):
    """Test successful auth token validation."""
    # Setup mock response
    mock_dynamodb.query.return_value = {
        'Items': [{
            'organization_id': 'test-org-123',
            'auth_token': 'test-token-456'
        }]
    }
    
    # Test validation
    is_valid, result = validate_auth_token('test-token-456', 'test-org-123')
    assert is_valid is True
    assert result['organization_id'] == 'test-org-123'
    
    # Verify mock was called correctly
    mock_dynamodb.query.assert_called_once_with(
        IndexName='AuthTokenIndex',
        KeyConditionExpression='auth_token = :token',
        ExpressionAttributeValues={':token': 'test-token-456'}
    )

def test_validate_auth_token_invalid_token(mock_dynamodb):
    """Test validation with invalid auth token."""
    # Setup mock response for no matching token
    mock_dynamodb.query.return_value = {'Items': []}
    
    # Test validation
    is_valid, result = validate_auth_token('invalid-token', 'test-org-123')
    assert is_valid is False
    assert result == "Invalid auth token"

def test_validate_auth_token_mismatched_org(mock_dynamodb):
    """Test validation with token belonging to different org."""
    # Setup mock response
    mock_dynamodb.query.return_value = {
        'Items': [{
            'organization_id': 'different-org',
            'auth_token': 'test-token-456'
        }]
    }
    
    # Test validation
    is_valid, result = validate_auth_token('test-token-456', 'test-org-123')
    assert is_valid is False
    assert result == "Auth token does not match organization ID"

def test_delete_organization_usage_data_success(mock_dynamodb):
    """Test successful deletion of usage data."""
    # Setup mock responses
    mock_dynamodb.query.return_value = {
        'Items': [
            {
                'organization_id': 'test-org-123',
                'record_id': 'record1'
            },
            {
                'organization_id': 'test-org-123',
                'record_id': 'record2'
            }
        ]
    }
    
    # Create mock batch writer
    mock_batch = MagicMock()
    mock_dynamodb.batch_writer.return_value.__enter__.return_value = mock_batch
    
    # Test deletion
    success, error = delete_organization_usage_data('test-org-123')
    assert success is True
    assert error is None
    
    # Verify mocks were called correctly
    assert mock_batch.delete_item.call_count == 2
    mock_batch.delete_item.assert_any_call(
        Key={
            'organization_id': 'test-org-123',
            'record_id': 'record1'
        }
    )

def test_lambda_handler_success(mock_dynamodb, valid_event):
    """Test successful organization deletion."""
    # Setup mock responses
    mock_dynamodb.query.return_value = {
        'Items': [{
            'organization_id': 'test-org-123',
            'auth_token': 'test-token-456'
        }]
    }
    mock_batch = MagicMock()
    mock_dynamodb.batch_writer.return_value.__enter__.return_value = mock_batch
    
    # Test handler
    response = lambda_handler(valid_event, {})
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['message'] == 'Organization and associated data deleted successfully'
    assert response_body['organization_id'] == 'test-org-123'

def test_lambda_handler_missing_body():
    """Test handler with missing request body."""
    response = lambda_handler({}, {})
    assert response['statusCode'] == 400
    assert 'Missing request body' in response['body']

def test_lambda_handler_missing_fields():
    """Test handler with missing required fields."""
    event = {'body': json.dumps({})}
    response = lambda_handler(event, {})
    assert response['statusCode'] == 400
    assert 'Missing required field' in response['body']

def test_lambda_handler_invalid_auth(mock_dynamodb, valid_event):
    """Test handler with invalid authentication."""
    # Setup mock response for invalid token
    mock_dynamodb.query.return_value = {'Items': []}
    
    # Test handler
    response = lambda_handler(valid_event, {})
    assert response['statusCode'] == 401
    assert 'Authentication failed' in response['body'] 