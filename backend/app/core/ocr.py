import os
import asyncio
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from PIL import Image
import io

from ..schemas.analysis import OCRResult

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Custom exception for OCR-related errors."""
    pass


class CheckFieldsSchema(BaseModel):
    """Pydantic schema for structured OCR extraction"""
    payee: Optional[str] = Field(None, description="The payee name on the check")
    amount: Optional[str] = Field(None, description="The amount written on the check")
    date: Optional[str] = Field(None, description="The date on the check")
    account_number: Optional[str] = Field(None, description="The account number")
    routing_number: Optional[str] = Field(None, description="The routing number")
    check_number: Optional[str] = Field(None, description="The check number")
    memo: Optional[str] = Field(None, description="The memo field content")
    bank_name: Optional[str] = Field(None, description="The bank name")
    signature_present: bool = Field(False, description="Whether a signature is present")
    raw_text: Optional[str] = Field(None, description="Raw extracted text")


class OCREngine:
    """
    OCR engine for extracting structured data from check images using Gemini API.
    
    Features:
    - Structured field extraction
    - Confidence scoring
    - Error handling and retries
    - Support for multiple image formats
    """
    
    def __init__(self, api_key: str):
        """
        Initialize OCR engine with Gemini API key.
        
        Args:
            api_key: Google Generative AI API key
        """
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-exp"
        self.max_retries = 3
        self.timeout = 30
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # OCR prompt template
        self.ocr_prompt = """
        Analyze this check image and extract the following information:
        
        1. Payee: The person or entity the check is written to
        2. Amount: The monetary amount (both numerical and written)
        3. Date: The date the check was written
        4. Account Number: The account number (usually at bottom)
        5. Routing Number: The routing number (usually at bottom left)
        6. Check Number: The check number (usually top right)
        7. Memo: Any memo or note written on the check
        8. Bank Name: The name of the bank
        9. Signature: Whether a signature is present
        10. Raw Text: All text visible on the check
        
        Please be very careful and accurate. If a field is not clearly visible or readable, 
        return null for that field. Pay special attention to:
        - Distinguishing between handwritten and printed text
        - Identifying potential alterations or tampering
        - Extracting numerical amounts accurately
        - Recognizing standard check formats
        
        Return the information in the exact JSON format specified.
        """
    
    async def extract_fields(self, image_path: str) -> OCRResult:
        """
        Extract structured fields from a check image.
        
        Args:
            image_path: Path to the check image file
            
        Returns:
            OCRResult with extracted fields and confidence scores
        """
        try:
            # Validate input
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Load and validate image
            image = await self._load_image(image_path)
            
            # Extract fields with retries
            extracted_data = await self._extract_with_retries(image, image_path)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_data)
            
            # Calculate overall extraction confidence
            overall_confidence = self._calculate_overall_confidence(confidence_scores)
            
            # Create OCR result
            ocr_result = OCRResult(
                payee=extracted_data.payee,
                amount=extracted_data.amount,
                date=extracted_data.date,
                account_number=extracted_data.account_number,
                routing_number=extracted_data.routing_number,
                check_number=extracted_data.check_number,
                memo=extracted_data.memo,
                signature_detected=extracted_data.signature_present,
                extraction_confidence=overall_confidence,
                raw_text=extracted_data.raw_text,
                field_confidences=confidence_scores
            )
            
            return ocr_result
            
        except FileNotFoundError:
            # Let FileNotFoundError propagate as-is
            raise
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {str(e)}")
            raise OCRError(f"Failed to extract fields from image: {str(e)}")
    
    async def _load_image(self, image_path: str) -> Image.Image:
        """Load and validate image file."""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if needed (handles RGBA, P, etc.)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Validate image format
            if image.format not in ['JPEG', 'PNG', 'WEBP']:
                # Save as temporary JPEG
                temp_path = f"{image_path}.temp.jpg"
                image.save(temp_path, 'JPEG', quality=90)
                image = Image.open(temp_path)
                
                # Clean up temp file
                os.remove(temp_path)
            
            # Validate image size
            if image.size[0] * image.size[1] > 4096 * 4096:
                # Resize if too large
                image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {str(e)}")
            raise
    
    async def _extract_with_retries(self, image: Image.Image, image_path: str) -> CheckFieldsSchema:
        """Extract fields with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Convert PIL Image to bytes
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='JPEG', quality=90)
                image_bytes.seek(0)
                
                # Call Gemini API
                response = await self._call_gemini_api(image_bytes.getvalue())
                
                # Parse response
                extracted_data = self._parse_gemini_response(response)
                
                return extracted_data
                
            except Exception as e:
                last_error = e
                logger.warning(f"OCR attempt {attempt + 1} failed for {image_path}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    break
        
        raise OCRError(f"OCR failed after {self.max_retries} attempts: {str(last_error)}")
    
    async def _call_gemini_api(self, image_bytes: bytes) -> GenerateContentResponse:
        """Call Gemini API for image analysis."""
        try:
            # Prepare image for API
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_k": 1,
                "top_p": 0.8,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
                "response_schema": CheckFieldsSchema.model_json_schema()
            }
            
            # Generate content
            response = self.model.generate_content(
                [self.ocr_prompt, image_part],
                generation_config=generation_config
            )
            
            # Check for blocked content
            if response.prompt_feedback.block_reason:
                raise OCRError(f"Content blocked: {response.prompt_feedback.block_reason}")
            
            # Check for safety issues
            if not response.candidates:
                raise OCRError("No candidates returned from API")
            
            candidate = response.candidates[0]
            if candidate.finish_reason != "STOP":
                raise OCRError(f"Generation stopped: {candidate.finish_reason}")
            
            return response
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise
    
    def _parse_gemini_response(self, response: GenerateContentResponse) -> CheckFieldsSchema:
        """Parse Gemini API response into structured data."""
        try:
            # Extract text from response
            if not response.candidates:
                raise OCRError("No candidates in response")
            
            candidate = response.candidates[0]
            if not candidate.content.parts:
                raise OCRError("No content parts in response")
            
            # Get JSON text
            json_text = candidate.content.parts[0].text
            
            # Parse JSON using Pydantic
            extracted_data = CheckFieldsSchema.model_validate_json(json_text)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {str(e)}")
            # Return empty schema on parse error
            return CheckFieldsSchema(
                payee=None,
                amount=None,
                date=None,
                account_number=None,
                routing_number=None,
                check_number=None,
                memo=None,
                bank_name=None,
                signature_present=False,
                raw_text=None
            )
    
    def _calculate_confidence_scores(self, extracted_data: CheckFieldsSchema) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields."""
        confidence_scores = {}
        
        # Base confidence based on field presence and format
        fields_to_check = [
            ('payee', extracted_data.payee),
            ('amount', extracted_data.amount),
            ('date', extracted_data.date),
            ('account_number', extracted_data.account_number),
            ('routing_number', extracted_data.routing_number),
            ('check_number', extracted_data.check_number),
            ('memo', extracted_data.memo),
            ('bank_name', extracted_data.bank_name)
        ]
        
        for field_name, field_value in fields_to_check:
            if field_value is None or field_value == "":
                confidence_scores[field_name] = 0.0
            else:
                # Basic confidence based on field characteristics
                confidence = self._calculate_field_confidence(field_name, field_value)
                confidence_scores[field_name] = confidence
        
        # Special handling for signature detection
        confidence_scores['signature_detected'] = 0.8 if extracted_data.signature_present else 0.9
        
        return confidence_scores
    
    def _calculate_field_confidence(self, field_name: str, field_value: str) -> float:
        """Calculate confidence for a specific field."""
        if not field_value:
            return 0.0
        
        base_confidence = 0.5
        
        # Field-specific confidence adjustments
        if field_name == 'amount':
            # Check if amount looks like a monetary value
            if '$' in field_value or any(c.isdigit() for c in field_value):
                base_confidence += 0.3
            if '.' in field_value:
                base_confidence += 0.1
        
        elif field_name == 'date':
            # Check if date looks like a date
            if any(month in field_value.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                base_confidence += 0.3
            if any(c.isdigit() for c in field_value):
                base_confidence += 0.2
        
        elif field_name in ['account_number', 'routing_number', 'check_number']:
            # Check if numbers look like bank identifiers
            if field_value.isdigit():
                base_confidence += 0.3
            if len(field_value) >= 6:  # Typical minimum length
                base_confidence += 0.2
        
        elif field_name == 'payee':
            # Check if payee looks like a name
            if len(field_value.split()) >= 2:
                base_confidence += 0.2
            if field_value.replace(' ', '').isalpha():
                base_confidence += 0.2
        
        # Length-based confidence
        if len(field_value) > 3:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _calculate_overall_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """Calculate overall extraction confidence."""
        if not confidence_scores:
            return 0.0
        
        # Weight important fields more heavily
        field_weights = {
            'payee': 0.2,
            'amount': 0.25,
            'date': 0.15,
            'account_number': 0.15,
            'routing_number': 0.1,
            'check_number': 0.1,
            'signature_detected': 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for field_name, confidence in confidence_scores.items():
            weight = field_weights.get(field_name, 0.05)
            weighted_sum += confidence * weight
            total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            overall_confidence = weighted_sum / total_weight
        else:
            overall_confidence = 0.0
        
        return min(1.0, overall_confidence)
    
    async def validate_extraction(self, ocr_result: OCRResult, image_path: str) -> Dict[str, Any]:
        """Validate OCR extraction results."""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check for required fields
            if not ocr_result.payee and not ocr_result.amount:
                validation_results['errors'].append('Neither payee nor amount extracted')
                validation_results['valid'] = False
            
            # Validate amount format
            if ocr_result.amount:
                if not any(c.isdigit() for c in ocr_result.amount):
                    validation_results['warnings'].append('Amount contains no digits')
            
            # Validate date format
            if ocr_result.date:
                if len(ocr_result.date) < 6:
                    validation_results['warnings'].append('Date appears too short')
            
            # Check confidence levels
            if ocr_result.extraction_confidence < 0.3:
                validation_results['warnings'].append('Low overall extraction confidence')
            
            # Check for potential tampering indicators
            if ocr_result.field_confidences:
                low_confidence_fields = [
                    field for field, conf in ocr_result.field_confidences.items() 
                    if conf < 0.2 and field in ['payee', 'amount', 'date']
                ]
                
                if low_confidence_fields:
                    validation_results['warnings'].append(
                        f'Low confidence in critical fields: {", ".join(low_confidence_fields)}'
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation failed for {image_path}: {str(e)}")
            validation_results['valid'] = False
            validation_results['errors'].append(f'Validation error: {str(e)}')
            return validation_results


# Helper functions
async def create_ocr_engine(api_key: Optional[str] = None) -> OCREngine:
    """
    Create and initialize OCR engine.
    
    Args:
        api_key: Optional API key, will use environment variable if not provided
        
    Returns:
        Configured OCR engine instance
    """
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY')
        
    if not api_key:
        raise OCRError("GEMINI_API_KEY environment variable not set")
    
    return OCREngine(api_key)


async def extract_check_fields(image_path: str, api_key: Optional[str] = None) -> OCRResult:
    """
    Convenience function to extract fields from a check image.
    
    Args:
        image_path: Path to the check image
        api_key: Optional API key
        
    Returns:
        OCRResult with extracted fields
    """
    engine = await create_ocr_engine(api_key)
    return await engine.extract_fields(image_path)