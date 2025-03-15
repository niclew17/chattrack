import pytest
import json
import subprocess
from unittest.mock import patch
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.test_auth import get_auth_token  # Import the function to test

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_TABLE'] = 'chatgpt_usage_tracking'
    os.environ['ORG_TABLE_NAME'] = 'chatgpt_organizations'

@patch('subprocess.run')
def test_get_auth_token_success(mock_run):
    """Test retrieving an auth token with mocked successful response."""
    # Mock the subprocess.run to return a successful response
    mock_response = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"auth_token": "test_token_12345", "organization_id": "org_123", "message": "Organization registered successfully"}',
        stderr='< HTTP/1.1 200 OK'
    )
    mock_run.return_value = mock_response
    
    # Run the test
    token = get_auth_token()
    
    # Verify the results
    assert token is not None
    assert token == "test_token_12345"
    assert isinstance(token, str)
    assert len(token) > 0
    assert os.environ.get('TEST_ORGANIZATION_ID') == "org_123"

@patch('subprocess.run')
def test_get_auth_token_error_400(mock_run):
    """Test handling of 400 error response when retrieving auth token."""
    # Mock the subprocess.run to return an error response
    mock_response = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"error": "Invalid organization name"}',
        stderr='< HTTP/1.1 400 Bad Request'
    )
    mock_run.return_value = mock_response
    
    # Run the test and verify it raises an exception
    with pytest.raises(Exception) as exc_info:
        get_auth_token()
    
    assert "Failed to retrieve auth token" in str(exc_info.value)
    assert "Invalid organization name" in str(exc_info.value)

@patch('subprocess.run')
def test_get_auth_token_error_500(mock_run):
    """Test handling of 500 error response when retrieving auth token."""
    # Mock the subprocess.run to return a server error response
    mock_response = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"error": "Internal server error"}',
        stderr='< HTTP/1.1 500 Internal Server Error'
    )
    mock_run.return_value = mock_response
    
    # Run the test and verify it raises an exception
    with pytest.raises(Exception) as exc_info:
        get_auth_token()
    
    assert "Failed to retrieve auth token" in str(exc_info.value)
    assert "Internal server error" in str(exc_info.value)

@patch('subprocess.run')
def test_get_auth_token_malformed_response(mock_run):
    """Test handling of malformed JSON response."""
    # Mock the subprocess.run to return a malformed response
    mock_response = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"malformed json',
        stderr='< HTTP/1.1 200 OK'
    )
    mock_run.return_value = mock_response
    
    # Run the test and verify it raises an exception
    with pytest.raises(Exception) as exc_info:
        get_auth_token()
    
    assert "Failed to retrieve auth token" in str(exc_info.value) 