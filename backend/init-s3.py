#!/usr/bin/env python3
"""
S3 Bucket Initialization Script for FraudCheck
This script creates the necessary S3 bucket in LocalStack for development
"""

import boto3
import os
from botocore.exceptions import ClientError


def main():
    # Configuration
    bucket_name = os.getenv('S3_BUCKET_NAME', 'FraudCheck-ai-bucket')
    aws_endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localstack:4566')
    aws_region = os.getenv('AWS_REGION', 'us-east-2')
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=aws_region,
        endpoint_url=aws_endpoint_url
    )
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ S3 bucket '{bucket_name}' already exists")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                if aws_region == 'us-east-1':
                    # For us-east-1, don't specify LocationConstraint
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': aws_region}
                    )
                print(f"✅ S3 bucket '{bucket_name}' created successfully")
                
                # Set bucket policy for development (LocalStack only)
                if 'localstack' in aws_endpoint_url:
                    bucket_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": "s3:GetObject",
                                "Resource": f"arn:aws:s3:::{bucket_name}/*"
                            }
                        ]
                    }
                    
                    try:
                        s3_client.put_bucket_policy(
                            Bucket=bucket_name,
                            Policy=str(bucket_policy).replace("'", '"')
                        )
                        print(f"✅ Bucket policy set for '{bucket_name}'")
                    except Exception as policy_error:
                        print(f"⚠️ Warning: Could not set bucket policy: {policy_error}")
                        
            except ClientError as create_error:
                print(f"❌ Failed to create bucket: {create_error}")
                exit(1)
        else:
            print(f"❌ Error checking bucket: {e}")
            exit(1)
    
    # List all buckets to confirm
    try:
        response = s3_client.list_buckets()
        print("\n📦 Available S3 buckets:")
        for bucket in response['Buckets']:
            print(f"  - {bucket['Name']}")
    except Exception as e:
        print(f"⚠️ Warning: Could not list buckets: {e}")


if __name__ == "__main__":
    main()
