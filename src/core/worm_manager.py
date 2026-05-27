"""WORM (Write Once Read Many) immutability manager using Wasabi Object Lock."""

import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Optional


class WORMManager:
    """Manages Wasabi Object Lock configuration for immutability."""
    
    def __init__(self, config: dict):
        """Initialize WORM manager with configuration.
        
        Args:
            config: Configuration dictionary with Wasabi credentials
        """
        self.config = config
        self._s3_client = None
    
    def _get_s3_client(self):
        """Get configured S3 client for Wasabi."""
        if self._s3_client is None:
            storage = self.config.get("storage", {})
            
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://s3.{storage.get('region', 'us-east-1')}.wasabisys.com",
                aws_access_key_id=storage.get("access_key", ""),
                aws_secret_access_key=storage.get("secret_key", ""),
                region_name=storage.get("region", "us-east-1")
            )
        
        return self._s3_client
    
    def enable_object_lock(self, bucket_name: str, retention_days: int = 90) -> Tuple[bool, str]:
        """Enable Object Lock on a bucket.
        
        Args:
            bucket_name: Name of the bucket
            retention_days: Retention period in days (default: 90)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            s3 = self._get_s3_client()
            
            # Enable object lock configuration on bucket
            s3.put_object_lock_configuration(
                Bucket=bucket_name,
                ObjectLockConfiguration={
                    "ObjectLockEnabled": "Enabled",
                    "Rule": {
                        "DefaultRetention": {
                            "Mode": "COMPLIANCE",
                            "Days": retention_days
                        }
                    }
                }
            )
            
            return True, f"Object Lock enabled on {bucket_name} with {retention_days} days retention"
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            
            if error_code == "ObjectLockConfigurationNotFoundError":
                # Bucket might not have object lock enabled at creation
                return False, "Object Lock must be enabled when bucket is created"
            elif error_code == "AccessDenied":
                return False, "Access denied: Check your credentials"
            else:
                return False, f"Failed to enable Object Lock: {e}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def get_object_lock_config(self, bucket_name: str) -> Tuple[bool, Optional[dict]]:
        """Get current Object Lock configuration for a bucket.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            Tuple of (success, config_dict)
        """
        try:
            s3 = self._get_s3_client()
            
            response = s3.get_object_lock_configuration(Bucket=bucket_name)
            return True, response.get("ObjectLockConfiguration")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ObjectLockConfigurationNotFoundError":
                return True, {"ObjectLockEnabled": "Disabled"}
            return False, None
        except Exception as e:
            return False, None
    
    def is_locked(self, bucket_name: str) -> bool:
        """Check if Object Lock is enabled on a bucket.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            True if locked, False otherwise
        """
        success, config = self.get_object_lock_config(bucket_name)
        if success and config:
            return config.get("ObjectLockEnabled") == "Enabled"
        return False
    
    def set_bucket_versioning(self, bucket_name: str) -> Tuple[bool, str]:
        """Enable versioning on a bucket (required for Object Lock).
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            Tuple of (success, message)
        """
        try:
            s3 = self._get_s3_client()
            
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={
                    "Status": "Enabled"
                }
            )
            
            return True, f"Versioning enabled on {bucket_name}"
            
        except ClientError as e:
            return False, f"Failed to enable versioning: {e}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def configure_bucket_for_worm(self, bucket_name: str, retention_days: int = 90) -> Tuple[bool, str]:
        """Configure a bucket for WORM immutability (enable versioning and object lock).
        
        Args:
            bucket_name: Name of the bucket
            retention_days: Retention period in days
        
        Returns:
            Tuple of (success, message)
        """
        # First enable versioning (required for Object Lock)
        success, msg = self.set_bucket_versioning(bucket_name)
        if not success:
            return False, f"Failed to enable versioning: {msg}"
        
        # Then enable Object Lock
        success, msg = self.enable_object_lock(bucket_name, retention_days)
        if not success:
            return False, f"Failed to enable Object Lock: {msg}"
        
        return True, f"Bucket {bucket_name} configured for WORM with {retention_days} days retention"
    
    def check_deletion_blocked(self, bucket_name: str) -> Tuple[bool, str]:
        """Check if deletion would be blocked by Object Lock.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            Tuple of (is_blocked, message)
        """
        if self.is_locked(bucket_name):
            return True, "Deletion blocked: Object Lock is enabled on this bucket"
        return False, "Deletion allowed: Object Lock is not enabled"
