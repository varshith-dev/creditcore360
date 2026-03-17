import logging
import asyncio
from typing import List, Optional
import aiofiles
import os
from pathlib import Path

from pillar1_ingestor.ocr_pipeline import ocr_pipeline
from pillar1_ingestor.textract_fallback import textract_fallback
from pillar1_ingestor.field_extractor import field_extractor
from pillar1_ingestor.cross_validator import cross_validator
from shared.models import DocumentType, ExtractedData, ValidationFlag

logger = logging.getLogger(__name__)

class DocumentRouter:
    """Main document processing router that orchestrates the entire pipeline"""
    
    def __init__(self):
        self.supported_formats = {
            'application/pdf': 'pdf',
            'image/jpeg': 'image',
            'image/png': 'image',
            'image/tiff': 'image'
        }
    
    async def process_uploaded_file(
        self, 
        file_path: str, 
        document_type: DocumentType,
        use_textract_fallback: bool = False
    ) -> ExtractedData:
        """
        Process a single uploaded file through the complete pipeline
        
        Args:
            file_path: Path to the uploaded file
            document_type: Type of document for field extraction
            use_textract_fallback: Force use of Textract instead of local OCR
            
        Returns:
            ExtractedData with fields and validation flags
        """
        try:
            logger.info(f"Processing document: {file_path} as {document_type}")
            
            # Read file bytes
            file_bytes = await self._read_file_bytes(file_path)
            mime_type = await self._detect_mime_type(file_path)
            
            if mime_type not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {mime_type}")
            
            # Step 1: OCR/Text Extraction
            if use_textract_fallback:
                extracted_doc = await textract_fallback.process_document(file_bytes, mime_type)
                # Convert Textract pages to ExtractedDocument format
                from shared.models import ExtractedDocument, PageResult
                pages = [PageResult(text=page.text, confidence=page.confidence, language=page.language) 
                        for page in extracted_doc]
                extracted_doc = ExtractedDocument(pages=pages, low_confidence_pages=[], total_pages=len(pages))
            else:
                extracted_doc = await ocr_pipeline.process_document(file_bytes, mime_type)
            
            # Check if Textract fallback is needed
            if (len(extracted_doc.low_confidence_pages) / extracted_doc.total_pages > 0.3 and 
                not use_textract_fallback and await textract_fallback.is_available()):
                
                logger.info("Low confidence detected, triggering Textract fallback")
                return await self.process_uploaded_file(file_path, document_type, use_textract_fallback=True)
            
            # Combine text from all pages
            full_text = '\n\n'.join([page.text for page in extracted_doc.pages])
            
            # Step 2: Field Extraction
            extracted_data = await field_extractor.extract_fields(full_text, document_type)
            
            # Step 3: Add OCR metadata
            extracted_data.extraction_confidence = min(
                extracted_data.extraction_confidence,
                100.0 * (1.0 - len(extracted_doc.low_confidence_pages) / extracted_doc.total_pages)
            )
            
            logger.info(f"Document processing completed: {document_type}, confidence: {extracted_data.extraction_confidence}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            # Return empty extraction with error flag
            return ExtractedData(
                document_type=document_type,
                extraction_confidence=0.0,
                validation_flags=[]
            )
    
    async def process_multiple_files(
        self, 
        file_paths: List[str], 
        document_types: List[DocumentType]
    ) -> List[ExtractedData]:
        """
        Process multiple files concurrently
        
        Args:
            file_paths: List of file paths
            document_types: Corresponding document types
            
        Returns:
            List of ExtractedData objects
        """
        try:
            if len(file_paths) != len(document_types):
                raise ValueError("Number of file paths must match number of document types")
            
            # Process all files concurrently
            tasks = [
                self.process_uploaded_file(file_path, doc_type)
                for file_path, doc_type in zip(file_paths, document_types)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return valid results
            valid_results = []
            for result in results:
                if isinstance(result, ExtractedData):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"File processing error: {result}")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Multiple file processing failed: {e}")
            return []
    
    async def run_cross_validation(self, extracted_data: List[ExtractedData]) -> List[ValidationFlag]:
        """
        Run cross-validation checks on all extracted data
        
        Args:
            extracted_data: List of ExtractedData objects
            
        Returns:
            List of validation flags
        """
        try:
            validation_flags = await cross_validator.validate_documents(extracted_data)
            
            # Add validation flags to respective extracted data objects
            flag_index = 0
            for data in extracted_data:
                # Distribute flags across documents (or add to all relevant ones)
                data.validation_flags.extend(validation_flags)
            
            logger.info(f"Cross-validation completed: {len(validation_flags)} flags generated")
            return validation_flags
            
        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return []
    
    async def _read_file_bytes(self, file_path: str) -> bytes:
        """Read file bytes asynchronously"""
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                return await file.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    async def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type based on file extension"""
        extension = Path(file_path).suffix.lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return list(self.supported_formats.keys())
    
    async def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files after processing"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

# Global instance
document_router = DocumentRouter()
