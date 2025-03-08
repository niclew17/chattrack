import json
import requests
import uuid

# Replace with your actual API Gateway endpoint URL
API_ENDPOINT = "https://your-api-gateway-endpoint.execute-api.region.amazonaws.com/stage/resource"

def test_chatgpt_usage_tracking():
    # Sample usage data
    payload = {
        "organization_id": "org_" + uuid.uuid4().hex[:8],  # Generate a random org ID for testing
        "model_name": "gpt-4",
        "input_tokens": 150,
        "output_tokens": 50,
        "user_id": f"user_{uuid.uuid4().hex[:8]}",  # Generate a random user ID for testing
        "session_id": "sess_67890",
        "prompt_type": "code_generation"
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