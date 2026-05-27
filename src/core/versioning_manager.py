"""Bucket Versioning Manager for Wasabi S3."""

import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Dict, Any


class VersioningManager:
    """Manages S3 bucket versioning."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize versioning manager.

        Args:
            config: Configuration dictionary with Wasabi credentials
        """
        self.config = config

    def _get_s3_client(self, region: str = None):
        """Get S3 client.

        Args:
            region: Optional region override. If not provided, uses sync_region.
        """
        storage = self.config.get("storage", {})
        region = region or storage.get("sync_region", "us-east-1")
        return boto3.client(
            's3',
            endpoint_url=f"https://s3.{region}.wasabisys.com",
            aws_access_key_id=storage.get("access_key"),
            aws_secret_access_key=storage.get("secret_key"),
            region_name=region
        )

    def get_versioning_status(self, bucket_name: str) -> Tuple[bool, str]:
        """Get versioning status of a bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Tuple of (success, message or status)
        """
        try:
            client = self._get_s3_client()
            response = client.get_bucket_versioning(Bucket=bucket_name)
            status = response.get('Status', 'Disabled')
            return True, f"Versioning status: {status}"
        except ClientError as e:
            return False, f"Failed to get versioning status: {str(e)}"

    def enable_versioning(self, bucket_name: str) -> Tuple[bool, str]:
        """Enable versioning on a bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Tuple of (success, message)
        """
        try:
            client = self._get_s3_client()

            # Check current status
            response = client.get_bucket_versioning(Bucket=bucket_name)
            current_status = response.get('Status', 'Disabled')

            if current_status == 'Enabled':
                return True, f"Versioning already enabled on bucket '{bucket_name}'"

            # Enable versioning
            client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={
                    'Status': 'Enabled'
                }
            )
            return True, f"Versioning enabled on bucket '{bucket_name}'"
        except ClientError as e:
            return False, f"Failed to enable versioning: {str(e)}"

    def disable_versioning(self, bucket_name: str) -> Tuple[bool, str]:
        """Disable versioning on a bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Tuple of (success, message)
        """
        try:
            client = self._get_s3_client()

            # Check current status
            response = client.get_bucket_versioning(Bucket=bucket_name)
            current_status = response.get('Status', 'Disabled')

            if current_status == 'Disabled':
                return True, f"Versioning already disabled on bucket '{bucket_name}'"

            # Disable versioning
            client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={
                    'Status': 'Suspended'
                }
            )
            return True, f"Versioning suspended on bucket '{bucket_name}'"
        except ClientError as e:
            return False, f"Failed to disable versioning: {str(e)}"
