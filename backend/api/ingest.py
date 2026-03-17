from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
import logging
import tempfile
import os
from pathlib import Path

from pillar1_ingestor.document_router import document_router
from shared.models import DocumentType

logger = logging.getLogger(__name__)

ingest_router = APIRouter()

@ingest_router.post("/ingest")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    document_types: Optional[List[str]] = Form(None)
):
    """Ingest and process uploaded documents"""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Map string types to DocumentType enum
        if document_types:
            doc_type_mapping = {
                "financial_statement": DocumentType.FINANCIAL_STATEMENT,
                "bank_statement": DocumentType.BANK_STATEMENT,
                "gst_return": DocumentType.GST_RETURN,
                "itr": DocumentType.ITR,
                "legal_collateral": DocumentType.LEGAL_COLLATERAL
            }
            
            mapped_types = []
            for doc_type_str in document_types:
                if doc_type_str in doc_type_mapping:
                    mapped_types.append(doc_type_mapping[doc_type_str])
                else:
                    # Default to financial statement if unknown type
                    mapped_types.append(DocumentType.FINANCIAL_STATEMENT)
        else:
            # Default all to financial statement
            mapped_types = [DocumentType.FINANCIAL_STATEMENT] * len(files)
        
        # Ensure we have types for all files
        while len(mapped_types) < len(files):
            mapped_types.append(DocumentType.FINANCIAL_STATEMENT)
        
        # Save uploaded files temporarily
        temp_file_paths = []
        try:
            for file in files:
                # Create temporary file
                suffix = Path(file.filename).suffix if file.filename else '.tmp'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_file_paths.append(temp_file.name)
            
            # Process documents through the pipeline
            extracted_data = await document_router.process_multiple_files(
                temp_file_paths, 
                mapped_types
            )
            
            # Run cross-validation
            validation_flags = await document_router.run_cross_validation(extracted_data)
            
            # Prepare results
            results = []
            for i, (file, data) in enumerate(zip(files, extracted_data)):
                file_info = {
                    "filename": file.filename,
                    "size": file.size,
                    "content_type": file.content_type,
                    "document_type": data.document_type.value,
                    "status": "processed",
                    "extraction_confidence": data.extraction_confidence,
                    "validation_flags_count": len(data.validation_flags),
                    "fields_extracted": bool(
                        data.financial_fields or 
                        data.bank_fields or 
                        data.gst_fields or 
                        data.itr_fields or 
                        data.legal_fields
                    )
                }
                results.append(file_info)
            
            return {
                "status": "success",
                "processed_files": len(results),
                "total_validation_flags": len(validation_flags),
                "results": results
            }
            
        finally:
            # Clean up temporary files
            await document_router.cleanup_temp_files(temp_file_paths)
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@ingest_router.get("/ingest/status/{session_id}")
async def get_ingestion_status(session_id: str):
    """Get status of document ingestion for a session"""
    # TODO: Implement session tracking
    return {
        "session_id": session_id,
        "status": "completed",
        "progress": 100,
        "message": "Ingestion pipeline implemented"
    }

@ingest_router.get("/ingest/formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "supported_formats": document_router.get_supported_formats(),
        "document_types": [
            "financial_statement",
            "bank_statement", 
            "gst_return",
            "itr",
            "legal_collateral"
        ]
    }
