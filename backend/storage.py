"""
Storage abstraction layer - supports both local filesystem and AWS S3
"""
import os
import io
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save_file(self, file_path: str, file_content: bytes) -> bool:
        """Save file to storage"""
        pass
    
    @abstractmethod
    def load_file(self, file_path: str) -> bytes:
        """Load file from storage"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> list:
        """List all files with optional prefix"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        pass


class LocalStorage(StorageBackend):
    """Store PDFs locally on filesystem"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
    
    def save_file(self, file_path: str, file_content: bytes) -> bool:
        """Save file to local filesystem"""
        try:
            full_path = os.path.join(self.base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(file_content)
            
            return os.path.exists(full_path) and os.path.getsize(full_path) > 0
        except Exception as e:
            print(f"Error saving file locally: {str(e)}")
            return False
    
    def load_file(self, file_path: str) -> bytes:
        """Load file from local filesystem"""
        try:
            full_path = os.path.join(self.base_path, file_path)
            if not os.path.exists(full_path):
                return None
            
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading file locally: {str(e)}")
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists locally"""
        full_path = os.path.join(self.base_path, file_path)
        return os.path.exists(full_path) and os.path.getsize(full_path) > 0
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        full_path = os.path.join(self.base_path, file_path)
        if os.path.exists(full_path):
            return os.path.getsize(full_path)
        return 0
    
    def list_files(self, prefix: str = "") -> list:
        """List all files"""
        try:
            files = []
            full_prefix_path = os.path.join(self.base_path, prefix) if prefix else self.base_path
            
            if os.path.exists(full_prefix_path):
                for filename in sorted(os.listdir(full_prefix_path)):
                    if filename.endswith('.pdf'):
                        filepath = os.path.join(full_prefix_path, filename)
                        if os.path.isfile(filepath):
                            files.append(filename)
            
            return files
        except Exception as e:
            print(f"Error listing files locally: {str(e)}")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        try:
            full_path = os.path.join(self.base_path, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
            return False


class S3Storage(StorageBackend):
    """Store PDFs in AWS S3"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1', 
                 access_key: str = None, secret_key: str = None):
        try:
            import boto3
            from botocore.exceptions import ClientError
            self.boto3 = boto3
            self.ClientError = ClientError
            
            # Use provided credentials or environment variables
            if access_key and secret_key:
                self.s3_client = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
            else:
                self.s3_client = boto3.client('s3', region_name=region)
            
            self.bucket_name = bucket_name
            
            # Test connection
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"[OK] S3 storage initialized: bucket={bucket_name}, region={region}")
            except self.ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise Exception(f"S3 Bucket '{bucket_name}' does not exist!")
                elif error_code == '403':
                    raise Exception(f"Access denied to S3 bucket '{bucket_name}'. Check AWS credentials!")
                else:
                    raise Exception(f"Cannot access S3 bucket: {str(e)}")
                    
        except ImportError:
            raise Exception("boto3 not installed. Install with: pip install boto3")
        except Exception as e:
            print(f"[ERROR] S3 Storage Error: {str(e)}")
            raise
    
    def save_file(self, file_path: str, file_content: bytes) -> bool:
        """Upload file to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content
            )
            print(f"[OK] Uploaded to S3: {file_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Error saving file to S3: {str(e)}")
            return False
    
    def load_file(self, file_path: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            content = response['Body'].read()
            return content
        except self.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            print(f"[ERROR] Error loading file from S3: {str(e)}")
            return None
        except Exception as e:
            print(f"[ERROR] Error loading file from S3: {str(e)}")
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except self.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            return False
        except Exception:
            return False
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size from S3"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return response['ContentLength']
        except Exception:
            return 0
    
    def list_files(self, prefix: str = "") -> list:
        """List all files in S3 with optional prefix"""
        try:
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.pdf') and not key.endswith('/'):
                            files.append(key.split('/')[-1])  # Return just filename
            
            return sorted(files)
        except Exception as e:
            print(f"[ERROR] Error listing S3 files: {str(e)}")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception as e:
            print(f"[ERROR] Error deleting S3 file: {str(e)}")
            return False


def get_storage_backend() -> StorageBackend:
    """Factory function to get the appropriate storage backend"""
    use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'
    
    if use_s3:
        bucket = os.getenv('AWS_S3_BUCKET')
        region = os.getenv('AWS_REGION', 'us-east-1')
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not bucket:
            raise ValueError("AWS_S3_BUCKET environment variable not set")
        
        return S3Storage(bucket, region, access_key, secret_key)
    else:
        # Use local storage
        local_path = os.getenv('PDF_STORAGE_PATH', os.path.join(os.path.dirname(__file__), 'output', 'pdfs'))
        return LocalStorage(local_path)
