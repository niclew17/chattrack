import pytest
import json
import subprocess
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
    register_url = "https://0sn8r3ie98.execute-api.us-east-1.amazonaws.com/Prod/register-organization"
    data = {
        "organization_name": "Test Company",
        "contact_email": "test@example.com"
    }
    curl_cmd = f'''curl -X POST "{register_url}" \\
        -H "Content-Type: application/json" \\
        -d '{json.dumps(data)}\''''
    response = run_curl_command(curl_cmd)
    if response['status_code'] == 200 and 'auth_token' in response['body']:
        return response['body']['auth_token']
    else:
        raise Exception("Failed to retrieve auth token")

def test_get_auth_token():
    """Test retrieving an auth token."""
    token = get_auth_token()
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    print(f"Successfully retrieved auth token: {token[:10]}...") 