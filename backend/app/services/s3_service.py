"""
S3 document storage service for JobApplicationTracker.

Handles upload, download, and presigned URL generation for
resumes, cover letters, and other application documents.

Usage:
    from app.services.s3_service import s3_service
    
    # Upload a file
    s3_key = await s3_service.upload_document(file_path, "resumes/resume.pdf")
    
    # Get a download URL (expires in 1 hour)
    url = await s3_service.get_download_url(s3_key)
    
    # Download content
    content = await s3_service.download_document(s3_key)
"""

import os
import asyncio
from typing import Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from ..logging_config import get_logger

logger = get_logger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "jobtracker-documents-245091941294")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class S3DocumentService:
    """Handles document storage in S3."""
    
    def __init__(self, bucket: Optional[str] = None, region: Optional[str] = None):
        self.bucket = bucket or S3_BUCKET
        self.region = region or AWS_REGION
        self._client = None
    
    @property
    def client(self):
        """Lazy-initialize S3 client."""
        if self._client is None:
            self._client = boto3.client("s3", region_name=self.region)
        return self._client
    
    async def upload_document(
        self,
        file_path: str,
        s3_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload a document to S3.
        
        Args:
            file_path: Local path to the file
            s3_key: S3 object key (e.g., "resumes/user1/resume_v2.pdf")
            content_type: MIME type of the file
            
        Returns:
            The S3 key where the file was stored
        """
        logger.info("Uploading document to S3", extra_fields={
            "s3_key": s3_key,
            "bucket": self.bucket,
            "file_path": file_path,
        })
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.upload_file(
                    file_path,
                    self.bucket,
                    s3_key,
                    ExtraArgs={"ContentType": content_type},
                ),
            )
            
            logger.info("Document uploaded successfully", extra_fields={
                "s3_key": s3_key,
            })
            return s3_key
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}", extra_fields={
                "s3_key": s3_key,
                "error": str(e),
            })
            raise
    
    async def upload_bytes(
        self,
        content: bytes,
        s3_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload bytes directly to S3.
        
        Args:
            content: File content as bytes
            s3_key: S3 object key
            content_type: MIME type
            
        Returns:
            The S3 key
        """
        logger.info("Uploading bytes to S3", extra_fields={
            "s3_key": s3_key,
            "size_bytes": len(content),
        })
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                ),
            )
            
            return s3_key
            
        except ClientError as e:
            logger.error(f"S3 upload bytes failed: {e}", extra_fields={
                "s3_key": s3_key,
                "error": str(e),
            })
            raise
    
    async def download_document(self, s3_key: str) -> bytes:
        """
        Download a document from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File content as bytes
        """
        logger.info("Downloading document from S3", extra_fields={
            "s3_key": s3_key,
        })
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.get_object(Bucket=self.bucket, Key=s3_key),
            )
            content = response["Body"].read()
            
            logger.info("Document downloaded", extra_fields={
                "s3_key": s3_key,
                "size_bytes": len(content),
            })
            return content
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}", extra_fields={
                "s3_key": s3_key,
                "error": str(e),
            })
            raise
    
    async def get_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned download URL.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL string
        """
        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": s3_key},
                    ExpiresIn=expires_in,
                ),
            )
            return url
            
        except ClientError as e:
            logger.error(f"Presigned URL generation failed: {e}", extra_fields={
                "s3_key": s3_key,
                "error": str(e),
            })
            raise
    
    async def delete_document(self, s3_key: str) -> bool:
        """
        Delete a document from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if deleted successfully
        """
        logger.info("Deleting document from S3", extra_fields={
            "s3_key": s3_key,
        })
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_object(Bucket=self.bucket, Key=s3_key),
            )
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}", extra_fields={
                "s3_key": s3_key,
                "error": str(e),
            })
            return False
    
    async def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.head_object(Bucket=self.bucket, Key=s3_key),
            )
            return True
        except ClientError:
            return False
    
    async def list_documents(self, prefix: str = "") -> list:
        """List documents with a given prefix."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix,
                ),
            )
            
            objects = response.get("Contents", [])
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                }
                for obj in objects
            ]
            
        except ClientError as e:
            logger.error(f"S3 list failed: {e}", extra_fields={
                "prefix": prefix,
                "error": str(e),
            })
            return []


# Global singleton instance
s3_service = S3DocumentService()
