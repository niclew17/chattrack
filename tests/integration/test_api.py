import json
import pytest
import requests
import os

@pytest.fixture
def api_endpoint():
    endpoint = os.getenv('API_ENDPOINT')
    if not endpoint:
        pytest.skip("API_ENDPOINT environment variable not set")
    return endpoint

def test_api_successful_request(api_endpoint):
    # Test data
    data = {
        'model_name': 'gpt-4',
        'input_tokens': 100,
        'output_tokens': 50,
        'user_id': 'test_user',
        'organization_id': 'test_org'
    }
    
    # Make request
    response = requests.post(api_endpoint, json=data)
    
    # Assert response
    assert response.status_code == 200
    body = response.json()
    assert body['message'] == 'Usage data recorded successfully'
    assert body['organization_id'] == 'test_org'
    assert body['user_id'] == 'test_user'
    assert 'total_cost' in body
    assert 'timestamp' in body

def test_api_missing_field(api_endpoint):
    # Test data missing required field
    data = {
        'model_name': 'gpt-4',
        'input_tokens': 100,
        # missing output_tokens
        'user_id': 'test_user',
        'organization_id': 'test_org'
    }
    
    # Make request
    response = requests.post(api_endpoint, json=data)
    
    # Assert response
    assert response.status_code == 400
    body = response.json()
    assert 'error' in body
    assert 'Missing required field' in body['error']

def test_api_invalid_model(api_endpoint):
    # Test data with invalid model
    data = {
        'model_name': 'invalid-model',
        'input_tokens': 100,
        'output_tokens': 50,
        'user_id': 'test_user',
        'organization_id': 'test_org'
    }
    
    # Make request
    response = requests.post(api_endpoint, json=data)
    
    # Assert response
    assert response.status_code == 400
    body = response.json()
    assert 'error' in body
    assert 'Unsupported model' in body['error'] 