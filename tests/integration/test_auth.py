import pytest
import json
import subprocess
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_curl_command(command):
    """Run a curl command and return the response."""
    try:
        # Add -v for verbose output and -k to allow insecure connections
        command = command.replace('curl', 'curl -v -k')
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"CURL Output: {result.stderr}")  # Print verbose output for debugging
        
        # Extract status code from verbose output
        status_code = None
        for line in result.stderr.split('\n'):
            if '< HTTP/' in line:  # Look for response headers
                try:
                    status_code = int(line.split()[2])  # Status code is the third element
                    break
                except (IndexError, ValueError):
                    continue
        
        # Try to parse response as JSON
        try:
            response_json = json.loads(result.stdout)
            # If we got JSON but no status code from headers, assume 200
            if status_code is None and isinstance(response_json, dict):
                status_code = 200
        except json.JSONDecodeError:
            response_json = None
            
        return {
            'status_code': status_code,
            'body': response_json if response_json else result.stdout
        }
    except subprocess.CalledProcessError as e:
        print(f"CURL Error: {e.stderr}")
        return {
            'status_code': None,
            'body': e.output
        }

def get_auth_token():
    """Register an organization and retrieve the auth token."""
    register_url = "https://wujhmm8lt4.execute-api.us-east-1.amazonaws.com/Prod/register-organization"
    data = {
        "organization_name": "Test Organization",
        "contact_email": "test@example.com",
        "description": "Test organization for integration testing"
    }
    
    # Properly escape the JSON data
    json_data = json.dumps(data).replace('"', '\\"')
    
    # Format the curl command with proper headers and data
    curl_cmd = f'curl -X POST "{register_url}" -H "Content-Type: application/json" -H "Accept: application/json" -d "{json_data}"'
    
    print(f"\nExecuting curl command: {curl_cmd}\n")  # Debug logging
    response = run_curl_command(curl_cmd)
    print(f"\nResponse: {response}\n")  # Debug logging
    
    if response['status_code'] == 200 and isinstance(response['body'], dict):
        if 'auth_token' in response['body']:
            # Store organization_id for future use if needed
            if 'organization_id' in response['body']:
                os.environ['TEST_ORGANIZATION_ID'] = response['body']['organization_id']
            return response['body']['auth_token']
    
    error_msg = response['body'].get('error', 'Unknown error') if isinstance(response['body'], dict) else response['body']
    raise Exception(f"Failed to retrieve auth token. Status: {response['status_code']}, Error: {error_msg}")

@pytest.mark.integration
def test_get_auth_token_integration():
    """Integration test for retrieving an auth token with real API call."""
    try:
        # Make the actual API call
        token = get_auth_token()
        
        # Verify the results
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        print(f"Successfully retrieved auth token from real API: {token[:10]}...")
        
        # Store the token for other integration tests if needed
        os.environ['TEST_AUTH_TOKEN'] = token
        
    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}")

@pytest.mark.integration
def test_get_auth_token_integration_duplicate():
    """Integration test for attempting to register the same organization twice."""
    try:
        # First registration should succeed
        token1 = get_auth_token()
        assert token1 is not None
        org_id1 = os.environ.get('TEST_ORGANIZATION_ID')
        
        # Second registration with same data should still work (idempotent)
        token2 = get_auth_token()
        assert token2 is not None
        org_id2 = os.environ.get('TEST_ORGANIZATION_ID')
        
        # The tokens should be different but both valid
        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0
        
        # Organization IDs should be different
        assert org_id1 != org_id2
        
    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}") 