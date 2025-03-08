import json
import requests
import uuid

# Replace with your actual API Gateway endpoint URL
API_ENDPOINT = "https://your-api-gateway-endpoint.execute-api.region.amazonaws.com/Prod/track"

def test_chatgpt_usage_tracking():
    # Generate a unique organization ID and user ID for testing
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    
    # Sample usage data
    payload = {
        "organization_id": org_id,
        "model_name": "gpt-4",
        "input_tokens": 150,
        "output_tokens": 50,
        "user_id": user_id,
        "cached_input_tokens": 100,  # Optional
        "reasoning_tokens": 0,       # Optional
        "session_id": "sess_67890",  # Additional metadata (optional)
        "prompt_type": "code_generation"  # Additional metadata (optional)
    }
    
    # Print the request payload
    print(f"Sending request with payload:\n{json.dumps(payload, indent=2)}")
    
    # Send POST request to the API
    response = requests.post(
        API_ENDPOINT,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    
    # Print the response
    print(f"\nResponse status code: {response.status_code}")
    print(f"Response body:\n{json.dumps(response.json(), indent=2) if response.text else 'No response body'}")
    
    return response

if __name__ == "__main__":
    test_chatgpt_usage_tracking() 