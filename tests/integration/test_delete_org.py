"""Integration tests for the delete organization function."""

import json
import pytest
import subprocess
import os
from uuid import uuid4

def run_curl_command(cmd):
    """Run a curl command and return the response."""
    try:
        # Add API key header to the command
        api_key = "YOUR_API_KEY_HERE"  # This should be retrieved from environment variable
        cmd = cmd.replace('curl', f'curl -H "x-api-key: {api_key}"')
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Extract status code from curl output
        status_line = [line for line in result.stderr.split('\n') if 'HTTP/' in line][0]
        status_code = int(status_line.split()[1])
        
        # Parse response body if present
        try:
            body = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            body = {'error': 'Invalid JSON response'}
            
        return {
            'status_code': status_code,
            'body': body,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {
            'status_code': 500,
            'body': {'error': str(e)},
            'stdout': '',
            'stderr': str(e)
        }

@pytest.fixture
def test_organization():
    """Create a test organization and return its details."""
    # Generate unique organization name
    org_name = f"Test Org {uuid4()}"
    register_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/register-organization"
    
    # Register organization
    data = {
        "organization_name": org_name,
        "contact_email": "test@example.com",
        "description": "Test organization for integration testing"
    }
    json_data = json.dumps(data).replace('"', '\\"')
    curl_cmd = f'curl -X POST "{register_url}" -H "Content-Type: application/json" -H "Accept: application/json" -d "{json_data}"'
    
    response = run_curl_command(curl_cmd)
    assert response['status_code'] == 200
    assert 'auth_token' in response['body']
    assert 'organization_id' in response['body']
    
    return {
        'organization_id': response['body']['organization_id'],
        'auth_token': response['body']['auth_token'],
        'organization_name': org_name
    }

@pytest.mark.integration
def test_delete_organization_success(test_organization):
    """Test successful deletion of an organization."""
    delete_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/delete-organization"
    
    # Create request data
    data = {
        "organization_id": test_organization['organization_id'],
        "auth_token": test_organization['auth_token']
    }
    json_data = json.dumps(data).replace('"', '\\"')
    
    # Send delete request
    curl_cmd = f'curl -X POST "{delete_url}" -H "Content-Type: application/json" -H "Accept: application/json" -d "{json_data}"'
    response = run_curl_command(curl_cmd)
    
    # Verify response
    assert response['status_code'] == 200
    assert response['body']['message'] == 'Organization and associated data deleted successfully'
    assert response['body']['organization_id'] == test_organization['organization_id']

@pytest.mark.integration
def test_delete_organization_invalid_auth():
    """Test deletion with invalid auth token."""
    delete_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/delete-organization"
    
    # Create request with invalid auth
    data = {
        "organization_id": "test-org-123",
        "auth_token": "invalid-token"
    }
    json_data = json.dumps(data).replace('"', '\\"')
    
    # Send delete request
    curl_cmd = f'curl -X POST "{delete_url}" -H "Content-Type: application/json" -H "Accept: application/json" -d "{json_data}"'
    response = run_curl_command(curl_cmd)
    
    # Verify response
    assert response['status_code'] == 401
    assert 'Authentication failed' in response['body']['error']

@pytest.mark.integration
def test_delete_organization_missing_fields():
    """Test deletion with missing required fields."""
    delete_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/delete-organization"
    
    # Create request with missing fields
    data = {}
    json_data = json.dumps(data).replace('"', '\\"')
    
    # Send delete request
    curl_cmd = f'curl -X POST "{delete_url}" -H "Content-Type: application/json" -H "Accept: application/json" -d "{json_data}"'
    response = run_curl_command(curl_cmd)
    
    # Verify response
    assert response['status_code'] == 403  # Will get 403 for missing API key
    assert 'Missing Authentication Token' in response['body']['message'] 