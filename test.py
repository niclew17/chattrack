import requests
import json
import time
import argparse
import boto3
from datetime import datetime, timedelta

def get_api_endpoints(stack_name, region='us-east-1'):
    """Get API endpoints from CloudFormation stack outputs"""
    cloudformation = boto3.client('cloudformation', region_name=region)
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        
        track_endpoint = next(
            (output['OutputValue'] for output in outputs if output['OutputKey'] == 'ApiEndpoint'),
            None
        )
        costs_endpoint = next(
            (output['OutputValue'] for output in outputs if output['OutputKey'] == 'GetCostsApiEndpoint'),
            None
        )
        
        if not track_endpoint or not costs_endpoint:
            raise ValueError("Could not find API endpoints in stack outputs")
            
        return track_endpoint, costs_endpoint
        
    except Exception as e:
        print(f"Error getting stack outputs: {str(e)}")
        raise

def test_track_endpoint(api_endpoint):
    print("\nTesting Track Endpoint...")
    
    # Test 1: Successful usage tracking
    print("\n1. Testing successful usage tracking...")
    response = requests.post(
        api_endpoint,
        headers={"Content-Type": "application/json"},
        json={
            "model_name": "gpt-4",
            "input_tokens": 100,
            "output_tokens": 50,
            "user_id": "test_user",
            "organization_id": "test_org"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200, "Expected 200 status code for successful request"
    
    # Test 2: Invalid model error
    print("\n2. Testing invalid model error...")
    response = requests.post(
        api_endpoint,
        headers={"Content-Type": "application/json"},
        json={
            "model_name": "invalid-model",
            "input_tokens": 100,
            "output_tokens": 50,
            "user_id": "test_user",
            "organization_id": "test_org"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 400, "Expected 400 status code for invalid model"
    
    # Test 3: Missing field error
    print("\n3. Testing missing field error...")
    response = requests.post(
        api_endpoint,
        headers={"Content-Type": "application/json"},
        json={
            "model_name": "gpt-4",
            "input_tokens": 100,
            "user_id": "test_user",
            "organization_id": "test_org"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 400, "Expected 400 status code for missing field"

def test_costs_endpoint(costs_api_endpoint):
    print("\nTesting Costs Endpoint...")
    
    # Wait for data to be available
    time.sleep(5)
    
    # Get date range for last 30 days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Test 4: Get costs with all parameters
    print("\n4. Testing get costs with all parameters...")
    response = requests.get(
        f"{costs_api_endpoint}",
        params={
            "organization_id": "test_org",
            "user_id": "test_user",
            "start_date": start_date,
            "end_date": end_date
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200, "Expected 200 status code for costs request with all parameters"
    
    # Test 5: Get costs by organization only
    print("\n5. Testing get costs by organization only...")
    response = requests.get(
        f"{costs_api_endpoint}",
        params={"organization_id": "test_org"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200, "Expected 200 status code for costs request by organization"
    
    # Test 6: Get costs by user only
    print("\n6. Testing get costs by user only...")
    response = requests.get(
        f"{costs_api_endpoint}",
        params={"user_id": "test_user"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200, "Expected 200 status code for costs request by user"
    
    # Test 7: Get costs with missing parameters
    print("\n7. Testing get costs with missing parameters...")
    response = requests.get(costs_api_endpoint)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 400, "Expected 400 status code for costs request with missing parameters"

def main():
    parser = argparse.ArgumentParser(description='Test ChatGPT Usage Tracking API endpoints')
    parser.add_argument('--stack-name', default='chatgpt-usage-tracker', help='CloudFormation stack name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--track-endpoint', help='Override the tracking API endpoint URL')
    parser.add_argument('--costs-endpoint', help='Override the costs API endpoint URL')
    
    args = parser.parse_args()
    
    try:
        # Get endpoints from CloudFormation if not provided
        if not args.track_endpoint or not args.costs_endpoint:
            print(f"Getting API endpoints from CloudFormation stack {args.stack_name}...")
            track_endpoint, costs_endpoint = get_api_endpoints(args.stack_name, args.region)
        else:
            track_endpoint = args.track_endpoint
            costs_endpoint = args.costs_endpoint
            
        print(f"Track Endpoint: {track_endpoint}")
        print(f"Costs Endpoint: {costs_endpoint}")
        
        # Run track endpoint tests
        test_track_endpoint(track_endpoint)
        
        # Run costs endpoint tests
        test_costs_endpoint(costs_endpoint)
        
        print("\nAll tests completed successfully!")
        
    except AssertionError as e:
        print(f"\nTest failed: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 