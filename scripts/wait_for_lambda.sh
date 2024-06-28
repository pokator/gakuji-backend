#!/bin/bash

FUNCTION_NAME=$1

# Specify the AWS region
REGION="us-east-2"

# Polling interval and timeout in seconds
POLL_INTERVAL=10
TIMEOUT=300

echo "Waiting for Lambda function $FUNCTION_NAME to become Active/Successful"

start_time=$(date +%s)

while : ; do
    current_time=$(date +%s)

    # Check if the timeout has been reached
    if [ $((current_time - start_time)) -ge $TIMEOUT ]; then
        echo "Timeout waiting for Lambda function to become Active/Successful."
        exit 1
    fi

    # Fetch the Lambda function's state and last update status
    result=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.[State, LastUpdateStatus]' --output text --region "$REGION")
    read -ra statuses <<< "$result"
    state="${statuses[0]}"
    last_update_status="${statuses[1]}"

    echo "Current state: $state, Last update status: $last_update_status"

    # Check if the function is in the desired state
    if [ "$state" == "Active" ] && [ "$last_update_status" == "Successful" ]; then
        echo "Lambda function $FUNCTION_NAME is Active and the last update was Successful."
        break
    else
        echo "Function is $state with last update status $last_update_status. Retrying in $POLL_INTERVAL seconds..."
        sleep $POLL_INTERVAL
    fi
done
