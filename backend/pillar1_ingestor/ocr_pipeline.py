import io
import logging
import asyncio
from typing import List, Tuple, Optional
import cv2
import numpy as np
import pytesseract
from PIL import Image
import pdfplumber
from pdf2image import convert_from_bytes

from config import config
from shared.models import PageResult, ExtractedDocument

logger = logging.getLogger(__name__)

class OCRPipeline:
    def __init__(self):
        self.confidence_threshold = config.OCR_CONFIDENCE_THRESHOLD
        self.languages = config.TESSERACT_LANGUAGES
        
    async def process_document(self, file_bytes: bytes, mime_type: str) -> ExtractedDocument:
        """
        Process document and extract text using OCR pipeline
        
        Args:
            file_bytes: Raw file bytes
            mime_type: MIME type of the file
            
        Returns:
            ExtractedDocument with pages and confidence information
        """
        try:
            if mime_type == "application/pdf":
                return await self._process_pdf(file_bytes)
            elif mime_type in ["image/jpeg", "image/png", "image/tiff"]:
                return await self._process_image(file_bytes)
            else:
                raise ValueError(f"Unsupported MIME type: {mime_type}")
                
        except Exception as e:
            logger.error(f"OCR pipeline failed: {e}")
            raise

    async def _process_pdf(self, pdf_bytes: bytes) -> ExtractedDocument:
        """Process PDF document with text extraction and OCR fallback"""
        pages = []
        low_confidence_pages = []
        
        try:
            # First try to extract text directly using pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    
                    if text and len(text.strip()) > 100:
                        # Good text extraction, no OCR needed
                        pages.append(PageResult(
                            text=text,
                            confidence=95.0,  # High confidence for digital text
                            language="eng"
                        ))
                    else:
                        # Need OCR for this page
                        image_pages = await self._convert_pdf_page_to_image(pdf_bytes, page_num)
                        for img_page in image_pages:
                            ocr_result = await self._process_image_page(img_page)
                            pages.append(ocr_result)
                            
                            if ocr_result.confidence < self.confidence_threshold:
                                low_confidence_pages.append(len(pages) - 1)
                                
        except Exception as e:
            logger.warning(f"pdfplumber failed, falling back to full OCR: {e}")
            # Fallback to full OCR
            image_pages = await self._convert_pdf_to_images(pdf_bytes)
            for i, img_page in enumerate(image_pages):
                ocr_result = await self._process_image_page(img_page)
                pages.append(ocr_result)
                
                if ocr_result.confidence < self.confidence_threshold:
                    low_confidence_pages.append(i)
        
        return ExtractedDocument(
            pages=pages,
            low_confidence_pages=low_confidence_pages,
            total_pages=len(pages)
        )

    async def _process_image(self, image_bytes: bytes) -> ExtractedDocument:
        """Process single image file"""
        image = Image.open(io.BytesIO(image_bytes))
        ocr_result = await self._process_image_page(image)
        
        low_confidence_pages = []
        if ocr_result.confidence < self.confidence_threshold:
            low_confidence_pages = [0]
            
        return ExtractedDocument(
            pages=[ocr_result],
            low_confidence_pages=low_confidence_pages,
            total_pages=1
        )

    async def _process_image_page(self, image: Image.Image) -> PageResult:
        """Process a single image page with OpenCV preprocessing and Tesseract OCR"""
        try:
            # Convert PIL Image to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocessing pipeline
            processed_image = await self._preprocess_image(opencv_image)
            
            # OCR with Tesseract
            pil_image = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # Configure Tesseract for better results
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            
            # Get OCR data with confidence scores
            ocr_data = pytesseract.image_to_data(
                pil_image,
                lang=self.languages,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and calculate confidence
            text_parts = []
            confidences = []
            
            for i in range(len(ocr_data['text'])):
                if int(ocr_data['conf'][i]) > 0:  # Skip empty/low confidence results
                    text_parts.append(ocr_data['text'][i])
                    confidences.append(ocr_data['conf'][i])
            
            text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            # Detect primary language
            language = await self._detect_language(text)
            
            return PageResult(
                text=text.strip(),
                confidence=float(avg_confidence),
                language=language
            )
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return PageResult(
                text="",
                confidence=0.0,
                language="unknown"
            )

    async def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply OpenCV preprocessing pipeline to improve OCR accuracy"""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Deskew the image
            deskewed = await self._deskew_image(gray)
            
            # Adaptive thresholding for better binarization
            binary = cv2.adaptiveThreshold(
                deskewed,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            
            # Denoising
            denoised = cv2.fastNlMeansDenoising(binary)
            
            return denoised
            
        except Exception as e:
            logger.warning(f"Preprocessing failed, using original image: {e}")
            return image

    async def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct skew in the image"""
        try:
            # Detect edges
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = theta * 180 / np.pi
                    if angle < 45:
                        angles.append(angle)
                    elif angle > 135:
                        angles.append(angle - 180)
                
                if angles:
                    median_angle = np.median(angles)
                    
                    # Rotate image to correct skew
                    if abs(median_angle) > 0.5:  # Only rotate if skew is significant
                        (h, w) = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                        return rotated
            
            return image
            
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
            return image

    async def _convert_pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Convert entire PDF to list of PIL Images"""
        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=300,  # High DPI for better OCR
                fmt='jpeg'
            )
            return images
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {e}")
            raise

    async def _convert_pdf_page_to_image(self, pdf_bytes: bytes, page_num: int) -> List[Image.Image]:
        """Convert specific PDF page to PIL Image"""
        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=300,
                first_page=page_num + 1,
                last_page=page_num + 1,
                fmt='jpeg'
            )
            return images
        except Exception as e:
            logger.error(f"PDF page {page_num} to image conversion failed: {e}")
            raise

    async def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        if not text:
            return "unknown"
            
        # Count Devanagari characters (Hindi)
        devanagari_count = sum(1 for char in text if '\u0900' <= char <= '\u097F')
        
        # Count Latin characters (English)
        latin_count = sum(1 for char in text if char.isascii() and char.isalpha())
        
        total_chars = devanagari_count + latin_count
        
        if total_chars == 0:
            return "unknown"
            
        devanagari_ratio = devanagari_count / total_chars
        
        if devanagari_ratio > 0.3:
            return "hin"
        elif latin_count > 0:
            return "eng"
        else:
            return "unknown"

# Global instance
ocr_pipeline = OCRPipeline()
