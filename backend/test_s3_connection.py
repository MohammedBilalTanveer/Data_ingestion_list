#!/usr/bin/env python3
"""
Test AWS S3 Connection
Run this to verify your S3 bucket and AWS credentials before running the app
"""
import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("AWS S3 Connection Test")
print("=" * 60)

# Load environment variables
load_dotenv()

# Check environment variables
print("\n1. Checking environment variables...")
print("-" * 60)

USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
print(f"   USE_S3: {USE_S3}")

if not USE_S3:
    print("   ✗ USE_S3 is not set to 'true'. Please update .env")
    sys.exit(1)

AWS_REGION = os.getenv('AWS_REGION')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')

print(f"   AWS_REGION: {AWS_REGION}")
print(f"   AWS_S3_BUCKET: {AWS_S3_BUCKET}")
print(f"   AWS_ACCESS_KEY_ID: {'*' * (len(AWS_ACCESS_KEY_ID) - 4) + AWS_ACCESS_KEY_ID[-4:] if AWS_ACCESS_KEY_ID else 'NOT SET'}")
print(f"   AWS_SECRET_ACCESS_KEY: {'*' * 20 if AWS_SECRET_ACCESS_KEY else 'NOT SET'}")

if not all([AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
    print("\n✗ Missing AWS credentials in .env!")
    sys.exit(1)

print("\n✓ All environment variables set")

# Test boto3 import
print("\n2. Testing boto3 import...")
print("-" * 60)

try:
    import boto3
    from botocore.exceptions import ClientError
    print("   ✓ boto3 imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import boto3: {str(e)}")
    print("   Install with: pip install boto3")
    sys.exit(1)

# Test S3 connection
print("\n3. Testing S3 bucket connection...")
print("-" * 60)

try:
    s3_client = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Test connection with head_bucket
    s3_client.head_bucket(Bucket=AWS_S3_BUCKET)
    print(f"   ✓ Successfully connected to S3 bucket: {AWS_S3_BUCKET}")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        print(f"   ✗ S3 Bucket '{AWS_S3_BUCKET}' does not exist!")
        print("   Create it in AWS S3 console or use AWS CLI:")
        print(f"   aws s3 mb s3://{AWS_S3_BUCKET} --region {AWS_REGION}")
    elif error_code == '403':
        print(f"   ✗ Access denied to S3 bucket '{AWS_S3_BUCKET}'")
        print("   Check your AWS credentials and IAM permissions")
    else:
        print(f"   ✗ S3 Error: {error_code} - {e.response['Error']['Message']}")
    sys.exit(1)
    
except Exception as e:
    print(f"   ✗ Connection failed: {str(e)}")
    print("   Check your AWS credentials")
    sys.exit(1)

# Test upload/download
print("\n4. Testing file upload and download...")
print("-" * 60)

try:
    test_file = "pdfs/test.txt"
    test_content = b"This is a test file from local machine"
    
    # Upload
    s3_client.put_object(
        Bucket=AWS_S3_BUCKET,
        Key=test_file,
        Body=test_content
    )
    print(f"   ✓ Test file uploaded: {test_file}")
    
    # Download
    response = s3_client.get_object(Bucket=AWS_S3_BUCKET, Key=test_file)
    downloaded = response['Body'].read()
    
    if downloaded == test_content:
        print(f"   ✓ Test file downloaded and verified")
    else:
        print(f"   ✗ Downloaded file doesn't match original")
        sys.exit(1)
    
    # Delete
    s3_client.delete_object(Bucket=AWS_S3_BUCKET, Key=test_file)
    print(f"   ✓ Test file deleted")
    
except Exception as e:
    print(f"   ✗ Upload/Download test failed: {str(e)}")
    sys.exit(1)

# Test storage.py
print("\n5. Testing storage.py...")
print("-" * 60)

try:
    from storage import get_storage_backend
    storage = get_storage_backend()
    print(f"   ✓ Storage backend initialized: {storage.__class__.__name__}")
    
except Exception as e:
    print(f"   ✗ Storage initialization failed: {str(e)}")
    sys.exit(1)

# Success!
print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nYour S3 setup is working correctly.")
print("You can now run: python backend_api.py")
print("\n" + "=" * 60)
