#!/bin/bash

API_ENDPOINT="https://hd83cf9mvd.execute-api.us-east-2.amazonaws.com/dev"
EXPECTED_STATUS=200

echo "Performing health check on $API_ENDPOINT"

response_status=$(curl -o /dev/null -s -w "%{http_code}\n" "$API_ENDPOINT")

if [ "$response_status" -eq "$EXPECTED_STATUS" ]; then
    echo "Health check passed with status $response_status"
else
    echo "Health check failed with status $response_status"
    exit 1
fi
