"""Integration tests for the delete organization function."""

import json
import pytest
import subprocess
from uuid import uuid4

def run_curl_command(cmd):
    """Run a curl command and return the response."""
    try:
        # Add verbose output for debugging
        cmd = cmd.replace('curl', 'curl -v -k')
        print(f"Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Curl stderr output: {result.stderr}")
        print(f"Curl stdout output: {result.stdout}")
        
        # Parse response body
        try:
            body = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            body = {}
            
        return {
            'body': body,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        print(f"Error in run_curl_command: {str(e)}")
        return {
            'body': {},
            'stdout': '',
            'stderr': str(e)
        }

def test_register_and_delete():
    """Test basic organization registration and deletion."""
    # Step 1: Register a new organization
    register_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/register-organization"
    org_name = f"Test Org {uuid4()}"
    
    register_data = {
        "organization_name": org_name,
        "contact_email": "test@example.com"
    }
    register_json = json.dumps(register_data).replace('"', '\\"')
    register_cmd = f'curl -X POST "{register_url}" -H "Content-Type: application/json" -d "{register_json}"'
    
    print("\n=== Registering Organization ===")
    register_response = run_curl_command(register_cmd)
    print(f"Registration response: {json.dumps(register_response['body'], indent=2)}")
    
    # Get organization details from response
    org_id = register_response['body']['organization_id']
    auth_token = register_response['body']['auth_token']
    
    # Step 2: Delete the organization
    delete_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/delete-organization"
    delete_data = {
        "organization_id": org_id,
        "auth_token": auth_token
    }
    delete_json = json.dumps(delete_data).replace('"', '\\"')
    delete_cmd = f'curl -X POST "{delete_url}" -H "Content-Type: application/json" -d "{delete_json}"'
    
    print("\n=== Deleting Organization ===")
    delete_response = run_curl_command(delete_cmd)
    print(f"Delete response: {json.dumps(delete_response['body'], indent=2)}")
    
    # Verify the responses
    assert 'organization_id' in register_response['body'], "Registration failed"
    assert 'message' in delete_response['body'], "Deletion failed" 