import io
import logging
import asyncio
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config import config
from shared.models import PageResult

logger = logging.getLogger(__name__)

class TextractFallback:
    """AWS Textract fallback for low-confidence OCR documents"""
    
    def __init__(self):
        try:
            self.client = boto3.client(
                'textract',
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                region_name=config.AWS_REGION
            )
            self.available = True
            logger.info("AWS Textract client initialized successfully")
        except (NoCredentialsError, Exception) as e:
            logger.warning(f"AWS Textract not available: {e}")
            self.client = None
            self.available = False

    async def process_document(self, file_bytes: bytes, mime_type: str) -> List[PageResult]:
        """
        Process document using AWS Textract
        
        Args:
            file_bytes: Raw file bytes
            mime_type: MIME type of the file
            
        Returns:
            List of PageResult with extracted text
        """
        if not self.available:
            raise RuntimeError("AWS Textract is not configured or available")
        
        try:
            if mime_type == "application/pdf":
                return await self._process_pdf(file_bytes)
            elif mime_type in ["image/jpeg", "image/png", "image/tiff"]:
                return [await self._process_image(file_bytes)]
            else:
                raise ValueError(f"Unsupported MIME type: {mime_type}")
                
        except Exception as e:
            logger.error(f"Textract processing failed: {e}")
            raise

    async def _process_pdf(self, pdf_bytes: bytes) -> List[PageResult]:
        """Process multi-page PDF using asynchronous Textract operations"""
        try:
            # Start asynchronous document analysis
            response = self.client.start_document_text_detection(
                Document={'Bytes': pdf_bytes}
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")
            
            # Wait for job completion
            pages_text = await self._wait_for_job_completion(job_id)
            
            # Convert to PageResult objects
            page_results = []
            for page_num, text in enumerate(pages_text):
                page_results.append(PageResult(
                    text=text,
                    confidence=90.0,  # Textract generally provides high confidence
                    language="eng"  # Textract auto-detects, default to English
                ))
            
            return page_results
            
        except ClientError as e:
            logger.error(f"Textract PDF processing failed: {e}")
            raise

    async def _process_image(self, image_bytes: bytes) -> PageResult:
        """Process single image using synchronous Textract"""
        try:
            response = self.client.detect_document_text(
                Document={'Bytes': image_bytes}
            )
            
            # Extract text from blocks
            text_parts = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_parts.append(block['Text'])
            
            text = '\n'.join(text_parts)
            
            return PageResult(
                text=text,
                confidence=90.0,
                language="eng"
            )
            
        except ClientError as e:
            logger.error(f"Textract image processing failed: {e}")
            raise

    async def _wait_for_job_completion(self, job_id: str, max_wait_time: int = 300) -> List[str]:
        """Wait for Textract job completion and retrieve results"""
        import time
        
        start_time = time.time()
        pages_text = {}
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check job status
                response = self.client.get_document_text_detection(JobId=job_id)
                status = response['JobStatus']
                
                logger.info(f"Textract job {job_id} status: {status}")
                
                if status == 'SUCCEEDED':
                    # Process results
                    pages_text = await self._process_textract_results(response)
                    break
                elif status == 'FAILED':
                    raise RuntimeError(f"Textract job {job_id} failed: {response.get('StatusMessage', 'Unknown error')}")
                elif status in ['IN_PROGRESS', 'PARTIAL_SUCCESS']:
                    # Continue waiting
                    await asyncio.sleep(5)
                else:
                    raise RuntimeError(f"Unexpected Textract job status: {status}")
                    
            except ClientError as e:
                logger.error(f"Error checking Textract job status: {e}")
                await asyncio.sleep(5)
        
        if not pages_text:
            raise TimeoutError(f"Textract job {job_id} did not complete within {max_wait_time} seconds")
        
        # Convert to list format (page numbers start from 1)
        max_page = max(pages_text.keys()) if pages_text else 0
        return [pages_text.get(page_num, "") for page_num in range(1, max_page + 1)]

    async def _process_textract_results(self, response: dict) -> dict[int, str]:
        """Process Textract response and extract text by page"""
        pages_text = {}
        current_page = 1
        text_lines = []
        
        for block in response['Blocks']:
            if block['BlockType'] == 'PAGE':
                # Save previous page text if any
                if text_lines:
                    pages_text[current_page] = '\n'.join(text_lines)
                    text_lines = []
                current_page = block.get('Page', current_page + 1)
                
            elif block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
        
        # Save last page text
        if text_lines:
            pages_text[current_page] = '\n'.join(text_lines)
        
        # Handle pagination if there are more results
        next_token = response.get('NextToken')
        while next_token:
            try:
                response = self.client.get_document_text_detection(
                    JobId=response['JobId'],
                    NextToken=next_token
                )
                
                for block in response['Blocks']:
                    if block['BlockType'] == 'PAGE':
                        if text_lines:
                            pages_text[current_page] = '\n'.join(text_lines)
                            text_lines = []
                        current_page = block.get('Page', current_page + 1)
                        
                    elif block['BlockType'] == 'LINE':
                        text_lines.append(block['Text'])
                
                next_token = response.get('NextToken')
                
            except ClientError as e:
                logger.error(f"Error processing Textract pagination: {e}")
                break
        
        # Save final page text
        if text_lines:
            pages_text[current_page] = '\n'.join(text_lines)
        
        return pages_text

    async def is_available(self) -> bool:
        """Check if Textract is available and configured"""
        if not self.available:
            return False
        
        try:
            # Test connection with a minimal request
            self.client.list_adapters(MaxResults=1)
            return True
        except Exception as e:
            logger.warning(f"Textract availability check failed: {e}")
            return False

# Global instance
textract_fallback = TextractFallback()
