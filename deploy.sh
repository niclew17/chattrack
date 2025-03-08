#!/bin/bash
set -e

# Configuration
STACK_NAME="chatgpt-usage-tracker"
REGION="us-east-1"  # Replace with your AWS region

# Check if AWS SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "AWS SAM CLI is not installed. Please install it first."
    echo "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

echo "Building the application..."
sam build

echo "Deploying the application..."
sam deploy \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --guided

echo "Deployment completed!"

# Get the API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text --region $REGION)

echo "API Endpoint: $API_ENDPOINT"
echo "Update the API_ENDPOINT variable in test_lambda.py with this URL to test the function." 