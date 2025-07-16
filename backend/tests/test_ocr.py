import pytest
import pytest_asyncio
from PIL import Image
import tempfile
import os
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import json

from app.core.ocr import OCREngine, OCRError, create_ocr_engine, CheckFieldsSchema
from app.schemas.analysis import OCRResult


@pytest.fixture
def mock_gemini_response():
    """Create a mock Gemini API response."""
    response = Mock()
    response.prompt_feedback.block_reason = None
    
    candidate = Mock()
    candidate.finish_reason = "STOP"
    candidate.content.parts = [Mock()]
    candidate.content.parts[0].text = json.dumps({
        "payee": "John Doe",
        "amount": "$100.00",
        "date": "2024-01-15",
        "account_number": "123456789",
        "routing_number": "987654321",
        "check_number": "001",
        "memo": "Test payment",
        "bank_name": "Test Bank",
        "signature_present": True,
        "raw_text": "Test check content"
    })
    
    response.candidates = [candidate]
    return response


@pytest.fixture
def sample_image():
    """Create a sample check image for testing."""
    # Create a simple test image
    image = Image.new('RGB', (400, 200), color='white')
    
    # Add some text-like patterns
    import PIL.ImageDraw
    draw = PIL.ImageDraw.Draw(image)
    draw.text((10, 10), "Test Bank", fill='black')
    draw.text((10, 30), "Pay to: John Doe", fill='black')
    draw.text((10, 50), "$100.00", fill='black')
    draw.text((10, 70), "Date: 01/15/2024", fill='black')
    draw.text((10, 90), "Memo: Test payment", fill='black')
    draw.text((10, 150), "123456789  987654321  001", fill='black')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def ocr_engine():
    """Create OCR engine for testing."""
    return OCREngine("test_api_key")


@pytest.mark.asyncio
async def test_create_ocr_engine():
    """Test OCR engine creation."""
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
        engine = await create_ocr_engine()
        assert engine is not None
        assert engine.api_key == 'test_key'


@pytest.mark.asyncio
async def test_create_ocr_engine_no_key():
    """Test OCR engine creation without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(OCRError):
            await create_ocr_engine()


@pytest.mark.asyncio
async def test_extract_fields_success(ocr_engine, sample_image, mock_gemini_response):
    """Test successful field extraction."""
    with patch.object(ocr_engine, '_call_gemini_api', return_value=mock_gemini_response):
        result = await ocr_engine.extract_fields(sample_image)
        
        assert isinstance(result, OCRResult)
        assert result.payee == "John Doe"
        assert result.amount == "$100.00"
        assert result.date == "2024-01-15"
        assert result.account_number == "123456789"
        assert result.routing_number == "987654321"
        assert result.check_number == "001"
        assert result.memo == "Test payment"
        assert result.signature_detected is True
        assert 0.0 <= result.extraction_confidence <= 1.0
        assert isinstance(result.field_confidences, dict)


@pytest.mark.asyncio
async def test_extract_fields_nonexistent_image(ocr_engine):
    """Test extraction with nonexistent image."""
    with pytest.raises(FileNotFoundError):
        await ocr_engine.extract_fields("nonexistent.jpg")


@pytest.mark.asyncio
async def test_extract_fields_with_retries(ocr_engine, sample_image):
    """Test extraction with retry logic."""
    # Mock API to fail twice then succeed
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "STOP"
    mock_response.candidates[0].content.parts = [Mock()]
    mock_response.candidates[0].content.parts[0].text = json.dumps({
        "payee": "John Doe",
        "amount": "$100.00",
        "date": "2024-01-15",
        "signature_present": True
    })
    
    with patch.object(ocr_engine, '_call_gemini_api') as mock_call:
        mock_call.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            mock_response
        ]
        
        result = await ocr_engine.extract_fields(sample_image)
        assert result.payee == "John Doe"
        assert mock_call.call_count == 3


@pytest.mark.asyncio
async def test_extract_fields_max_retries_exceeded(ocr_engine, sample_image):
    """Test extraction when max retries exceeded."""
    with patch.object(ocr_engine, '_call_gemini_api') as mock_call:
        mock_call.side_effect = Exception("Persistent API Error")
        
        with pytest.raises(OCRError):
            await ocr_engine.extract_fields(sample_image)
        
        assert mock_call.call_count == ocr_engine.max_retries


@pytest.mark.asyncio
async def test_load_image_success(ocr_engine, sample_image):
    """Test successful image loading."""
    image = await ocr_engine._load_image(sample_image)
    assert image is not None
    assert image.format in ['JPEG', 'PNG']


@pytest.mark.asyncio
async def test_load_image_format_conversion(ocr_engine):
    """Test image format conversion."""
    # Create a PNG image
    png_image = Image.new('RGBA', (100, 100), color=(255, 255, 255, 128))
    png_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    png_image.save(png_temp.name, 'PNG')
    png_temp.close()
    
    try:
        loaded_image = await ocr_engine._load_image(png_temp.name)
        assert loaded_image is not None
        assert loaded_image.mode == 'RGB'  # Should be converted
    finally:
        os.unlink(png_temp.name)


@pytest.mark.asyncio
async def test_load_image_resize_large(ocr_engine):
    """Test image resizing for large images."""
    # Create a large image
    large_image = Image.new('RGB', (5000, 5000), color='white')
    large_temp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    large_image.save(large_temp.name, 'JPEG')
    large_temp.close()
    
    try:
        loaded_image = await ocr_engine._load_image(large_temp.name)
        assert loaded_image is not None
        assert max(loaded_image.size) <= 4096  # Should be resized
    finally:
        os.unlink(large_temp.name)


@pytest.mark.asyncio
async def test_call_gemini_api_success(ocr_engine):
    """Test successful Gemini API call."""
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "STOP"
    
    with patch.object(ocr_engine.model, 'generate_content', return_value=mock_response):
        result = await ocr_engine._call_gemini_api(b'test_image_bytes')
        assert result == mock_response


@pytest.mark.asyncio
async def test_call_gemini_api_blocked_content(ocr_engine):
    """Test Gemini API call with blocked content."""
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = "SAFETY"
    
    with patch.object(ocr_engine.model, 'generate_content', return_value=mock_response):
        with pytest.raises(OCRError):
            await ocr_engine._call_gemini_api(b'test_image_bytes')


@pytest.mark.asyncio
async def test_call_gemini_api_no_candidates(ocr_engine):
    """Test Gemini API call with no candidates."""
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = []
    
    with patch.object(ocr_engine.model, 'generate_content', return_value=mock_response):
        with pytest.raises(OCRError):
            await ocr_engine._call_gemini_api(b'test_image_bytes')


@pytest.mark.asyncio
async def test_call_gemini_api_finish_reason_error(ocr_engine):
    """Test Gemini API call with finish reason error."""
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "ERROR"
    
    with patch.object(ocr_engine.model, 'generate_content', return_value=mock_response):
        with pytest.raises(OCRError):
            await ocr_engine._call_gemini_api(b'test_image_bytes')


@pytest.mark.asyncio
async def test_parse_gemini_response_success(ocr_engine, mock_gemini_response):
    """Test successful Gemini response parsing."""
    result = ocr_engine._parse_gemini_response(mock_gemini_response)
    
    assert isinstance(result, CheckFieldsSchema)
    assert result.payee == "John Doe"
    assert result.amount == "$100.00"
    assert result.signature_present is True


@pytest.mark.asyncio
async def test_parse_gemini_response_invalid_json(ocr_engine):
    """Test parsing invalid JSON response."""
    mock_response = Mock()
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].content.parts = [Mock()]
    mock_response.candidates[0].content.parts[0].text = "invalid json"
    
    result = ocr_engine._parse_gemini_response(mock_response)
    
    # Should return empty schema on parse error
    assert isinstance(result, CheckFieldsSchema)
    assert result.payee is None


@pytest.mark.asyncio
async def test_parse_gemini_response_no_candidates(ocr_engine):
    """Test parsing response with no candidates."""
    mock_response = Mock()
    mock_response.candidates = []
    
    result = ocr_engine._parse_gemini_response(mock_response)
    assert isinstance(result, CheckFieldsSchema)


@pytest.mark.asyncio
async def test_calculate_confidence_scores(ocr_engine):
    """Test confidence score calculation."""
    extracted_data = CheckFieldsSchema(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        account_number="123456789",
        routing_number="987654321",
        check_number="001",
        signature_present=True
    )
    
    result = ocr_engine._calculate_confidence_scores(extracted_data)
    
    assert isinstance(result, dict)
    assert 'payee' in result
    assert 'amount' in result
    assert 'date' in result
    assert 'signature_detected' in result
    
    # All scores should be between 0 and 1
    for score in result.values():
        assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_calculate_field_confidence_amount(ocr_engine):
    """Test field confidence calculation for amount."""
    # Good amount format
    confidence = ocr_engine._calculate_field_confidence('amount', '$100.00')
    assert confidence > 0.5
    
    # Amount with no currency symbol
    confidence = ocr_engine._calculate_field_confidence('amount', '100.00')
    assert confidence > 0.5
    
    # Invalid amount
    confidence = ocr_engine._calculate_field_confidence('amount', 'invalid')
    assert confidence < 0.8


@pytest.mark.asyncio
async def test_calculate_field_confidence_date(ocr_engine):
    """Test field confidence calculation for date."""
    # Good date format
    confidence = ocr_engine._calculate_field_confidence('date', 'January 15, 2024')
    assert confidence > 0.5
    
    # Date with digits
    confidence = ocr_engine._calculate_field_confidence('date', '01/15/2024')
    assert confidence > 0.5
    
    # Invalid date
    confidence = ocr_engine._calculate_field_confidence('date', 'invalid')
    assert confidence < 0.8


@pytest.mark.asyncio
async def test_calculate_field_confidence_numbers(ocr_engine):
    """Test field confidence calculation for numeric fields."""
    # Good account number
    confidence = ocr_engine._calculate_field_confidence('account_number', '123456789')
    assert confidence > 0.5
    
    # Short number
    confidence = ocr_engine._calculate_field_confidence('account_number', '123')
    assert confidence <= 0.8
    
    # Non-numeric
    confidence = ocr_engine._calculate_field_confidence('account_number', 'abc123')
    assert confidence < 0.8


@pytest.mark.asyncio
async def test_calculate_field_confidence_payee(ocr_engine):
    """Test field confidence calculation for payee."""
    # Good payee name
    confidence = ocr_engine._calculate_field_confidence('payee', 'John Doe')
    assert confidence > 0.5
    
    # Single word
    confidence = ocr_engine._calculate_field_confidence('payee', 'John')
    assert confidence < 0.8
    
    # Contains numbers
    confidence = ocr_engine._calculate_field_confidence('payee', 'John123')
    assert confidence < 0.8


@pytest.mark.asyncio
async def test_calculate_overall_confidence(ocr_engine):
    """Test overall confidence calculation."""
    confidence_scores = {
        'payee': 0.8,
        'amount': 0.9,
        'date': 0.7,
        'account_number': 0.6,
        'routing_number': 0.5,
        'signature_detected': 0.8
    }
    
    result = ocr_engine._calculate_overall_confidence(confidence_scores)
    
    assert 0.0 <= result <= 1.0
    # Should be weighted average favoring important fields
    assert result > 0.5  # With these scores, should be reasonably high


@pytest.mark.asyncio
async def test_validate_extraction_success(ocr_engine, sample_image):
    """Test successful extraction validation."""
    ocr_result = OCRResult(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        account_number="123456789",
        routing_number="987654321",
        check_number="001",
        signature_detected=True,
        extraction_confidence=0.8,
        field_confidences={}
    )
    
    result = await ocr_engine.validate_extraction(ocr_result, sample_image)
    
    assert isinstance(result, dict)
    assert 'valid' in result
    assert 'warnings' in result
    assert 'errors' in result
    assert result['valid'] is True


@pytest.mark.asyncio
async def test_validate_extraction_missing_fields(ocr_engine, sample_image):
    """Test extraction validation with missing fields."""
    ocr_result = OCRResult(
        payee=None,
        amount=None,
        date=None,
        signature_detected=False,
        extraction_confidence=0.3,
        field_confidences={}
    )
    
    result = await ocr_engine.validate_extraction(ocr_result, sample_image)
    
    assert result['valid'] is False
    assert len(result['errors']) > 0


@pytest.mark.asyncio
async def test_validate_extraction_warnings(ocr_engine, sample_image):
    """Test extraction validation with warnings."""
    ocr_result = OCRResult(
        payee="John Doe",
        amount="invalid amount",
        date="1/1",  # Too short
        signature_detected=True,
        extraction_confidence=0.2,  # Low confidence
        field_confidences={'payee': 0.1, 'amount': 0.1}
    )
    
    result = await ocr_engine.validate_extraction(ocr_result, sample_image)
    
    assert len(result['warnings']) > 0


@pytest.mark.asyncio
async def test_extract_check_fields_convenience_function(sample_image, ocr_engine):
    """Test the convenience function for field extraction."""
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "STOP"
    mock_response.candidates[0].content.parts = [Mock()]
    mock_response.candidates[0].content.parts[0].text = json.dumps({
        "payee": "John Doe",
        "amount": "$100.00",
        "signature_present": True
    })
    
    with patch('app.core.ocr.OCREngine._call_gemini_api', return_value=mock_response):
        result = await ocr_engine.extract_fields(sample_image)
        assert result.payee == "John Doe"


@pytest.mark.asyncio
async def test_ocr_engine_initialization():
    """Test OCR engine initialization."""
    engine = OCREngine("test_key")
    
    assert engine.api_key == "test_key"
    assert engine.model_name == "gemini-2.0-flash-exp"
    assert engine.max_retries == 3
    assert engine.timeout == 30
    assert engine.ocr_prompt is not None


@pytest.mark.asyncio
async def test_check_fields_schema_validation():
    """Test CheckFieldsSchema validation."""
    # Valid data
    schema = CheckFieldsSchema(
        payee="John Doe",
        amount="$100.00",
        date="2024-01-15",
        signature_present=True
    )
    
    assert schema.payee == "John Doe"
    assert schema.amount == "$100.00"
    assert schema.signature_present is True
    
    # None values should be allowed
    schema = CheckFieldsSchema(
        payee=None,
        amount=None,
        signature_present=False
    )
    
    assert schema.payee is None
    assert schema.amount is None
    assert schema.signature_present is False


@pytest.mark.asyncio
async def test_ocr_error_handling(ocr_engine, sample_image):
    """Test OCR error handling."""
    # Test with various API errors
    with patch.object(ocr_engine, '_call_gemini_api') as mock_call:
        mock_call.side_effect = Exception("API Error")
        
        with pytest.raises(OCRError):
            await ocr_engine.extract_fields(sample_image)


@pytest.mark.asyncio
async def test_ocr_memory_management(ocr_engine, sample_image):
    """Test OCR memory management."""
    # Run multiple extractions to test memory cleanup
    mock_response = Mock()
    mock_response.prompt_feedback.block_reason = None
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "STOP"
    mock_response.candidates[0].content.parts = [Mock()]
    mock_response.candidates[0].content.parts[0].text = json.dumps({"payee": "Test"})
    
    with patch.object(ocr_engine, '_call_gemini_api', return_value=mock_response):
        for _ in range(5):
            result = await ocr_engine.extract_fields(sample_image)
            assert result is not None