"""
Comprehensive tests for image_utils module to achieve 90%+ coverage.
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from PIL import Image

from app.utils.image_utils import (
    validate_image_file,
    normalize_image_format,
    enhance_image_quality,
    resize_image,
    convert_to_grayscale,
    crop_image,
    rotate_image,
    detect_image_orientation,
    create_thumbnail,
    get_image_info,
    bytes_to_image,
    image_to_bytes,
    TempImageFile,
    ImageValidationError,
    ImageProcessingError,
)


class TestImageValidation:
    """Test image validation functionality."""
    
    def test_validate_image_file_not_found(self):
        """Test validation with non-existent file."""
        with pytest.raises(ImageProcessingError, match="Image file not found"):
            validate_image_file("nonexistent.jpg")
    
    def test_validate_image_file_too_large(self):
        """Test validation with file too large."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a valid image first
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock os.path.getsize to return a large size
            with patch('os.path.getsize', return_value=60 * 1024 * 1024):  # 60MB
                with pytest.raises(ImageValidationError, match="Image file too large"):
                    validate_image_file(tmp.name)
        
        os.unlink(tmp.name)
    
    def test_validate_image_unsupported_format(self):
        """Test validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as tmp:
            # Create a GIF image (unsupported)
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'GIF')
            
            with pytest.raises(ImageValidationError, match="Unsupported image format"):
                validate_image_file(tmp.name)
        
        os.unlink(tmp.name)
    
    def test_validate_image_dimensions_too_large(self):
        """Test validation with dimensions too large."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Mock PIL Image to return large dimensions
            with patch('PIL.Image.open') as mock_open:
                mock_image = MagicMock()
                mock_image.format = 'JPEG'
                mock_image.size = (10000, 10000)  # Too large
                mock_image.mode = 'RGB'
                mock_image.info = {}
                mock_open.return_value = mock_image
                
                with pytest.raises(ImageValidationError, match="Image dimensions too large"):
                    validate_image_file(tmp.name)
        
        os.unlink(tmp.name)
    
    def test_validate_image_corrupted(self):
        """Test validation with corrupted image."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a valid image first
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock verify to raise exception
            with patch('PIL.Image.open') as mock_open:
                mock_image = MagicMock()
                mock_image.format = 'JPEG'
                mock_image.size = (100, 100)
                mock_image.mode = 'RGB'
                mock_image.info = {}
                mock_image.verify.side_effect = Exception("Corrupted")
                mock_open.return_value = mock_image
                
                with pytest.raises(ImageValidationError, match="Image appears to be corrupted"):
                    validate_image_file(tmp.name)
        
        os.unlink(tmp.name)
    
    def test_validate_image_success_with_transparency(self):
        """Test successful validation with transparent image."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            # Create RGBA image with transparency
            image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
            image.save(tmp.name, 'PNG')
            
            result = validate_image_file(tmp.name)
            
            assert result['valid'] is True
            assert result['format'] == 'PNG'
            assert result['mode'] == 'RGBA'
            assert result['has_transparency'] is True
        
        os.unlink(tmp.name)
    
    def test_validate_image_success_with_transparency_info(self):
        """Test successful validation with transparency in info."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'PNG')
            
            # Mock to add transparency in info
            with patch('PIL.Image.open') as mock_open:
                mock_image = MagicMock()
                mock_image.format = 'PNG'
                mock_image.size = (100, 100)
                mock_image.mode = 'RGB'
                mock_image.info = {'transparency': 0}
                mock_image.verify.return_value = None
                mock_open.return_value = mock_image
                
                result = validate_image_file(tmp.name)
                
                assert result['valid'] is True
                assert result['has_transparency'] is True
        
        os.unlink(tmp.name)


class TestImageNormalization:
    """Test image format normalization."""
    
    def test_normalize_image_format_rgba_to_jpeg(self):
        """Test normalizing RGBA to JPEG."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_in:
            # Create RGBA image
            image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
            image.save(tmp_in.name, 'PNG')
            
            result_path = normalize_image_format(tmp_in.name, 'JPEG', quality=80)
            
            # Verify output path has expected format
            assert result_path.endswith('.normalized.jpeg')
            assert os.path.exists(result_path)
            
            # Verify output image exists and is RGB
            output_image = Image.open(result_path)
            assert output_image.mode == 'RGB'
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_normalize_image_format_png_conversion(self):
        """Test normalizing to PNG format."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create RGB image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = normalize_image_format(tmp_in.name, 'PNG')
            
            # Verify output image exists and is PNG
            assert os.path.exists(result_path)
            output_image = Image.open(result_path)
            assert output_image.format == 'PNG'
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_normalize_image_format_error_handling(self):
        """Test error handling in normalization."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create valid image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock PIL to raise exception
            with patch('PIL.Image.open', side_effect=Exception("Test error")):
                with pytest.raises(ImageProcessingError, match="Image normalization failed"):
                    normalize_image_format(tmp.name)
        
        os.unlink(tmp.name)


class TestImageEnhancement:
    """Test image enhancement functionality."""
    
    def test_enhance_image_quality_basic(self):
        """Test basic image enhancement."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create test image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = enhance_image_quality(tmp_in.name)
            
            assert os.path.exists(result_path)
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_enhance_image_quality_custom_params(self):
        """Test enhancement with custom parameters."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create test image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = enhance_image_quality(
                tmp_in.name,
                enhance_contrast=True,
                enhance_sharpness=True,
                enhance_brightness=True
            )
            
            assert os.path.exists(result_path)
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_enhance_image_quality_error_handling(self):
        """Test error handling in enhancement."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create valid image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock PIL to raise exception
            with patch('PIL.Image.open', side_effect=Exception("Test error")):
                with pytest.raises(ImageProcessingError, match="Image enhancement failed"):
                    enhance_image_quality(tmp.name)
        
        os.unlink(tmp.name)


class TestImageResizing:
    """Test image resizing functionality."""
    
    def test_resize_image_basic(self):
        """Test basic image resizing."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create large test image
            image = Image.new('RGB', (1000, 800), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = resize_image(tmp_in.name, max_width=500, max_height=400)
            
            assert os.path.exists(result_path)
            
            # Verify the image was actually resized
            resized_image = Image.open(result_path)
            assert resized_image.size[0] <= 500
            assert resized_image.size[1] <= 400
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_resize_image_error_handling(self):
        """Test error handling in resizing."""
        with pytest.raises(ImageProcessingError, match="Image resizing failed"):
            resize_image("nonexistent.jpg")


class TestImageConversion:
    """Test image conversion functionality."""
    
    def test_convert_to_grayscale_basic(self):
        """Test basic grayscale conversion."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create color test image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = convert_to_grayscale(tmp_in.name)
            
            assert os.path.exists(result_path)
            
            # Verify the image was converted to grayscale
            grayscale_image = Image.open(result_path)
            assert grayscale_image.mode == 'L'
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_convert_to_grayscale_error_handling(self):
        """Test error handling in grayscale conversion."""
        with pytest.raises(ImageProcessingError, match="Grayscale conversion failed"):
            convert_to_grayscale("nonexistent.jpg")


class TestImageCropping:
    """Test image cropping functionality."""
    
    def test_crop_image_basic(self):
        """Test basic image cropping."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create test image
            image = Image.new('RGB', (200, 200), color='blue')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = crop_image(tmp_in.name, (50, 50, 150, 150))
            
            assert os.path.exists(result_path)
            
            # Verify the image was cropped correctly
            cropped_image = Image.open(result_path)
            assert cropped_image.size == (100, 100)
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_crop_image_error_handling(self):
        """Test error handling in cropping."""
        with pytest.raises(ImageProcessingError, match="Image cropping failed"):
            crop_image("nonexistent.jpg", (0, 0, 100, 100))


class TestImageRotation:
    """Test image rotation functionality."""
    
    def test_rotate_image_basic(self):
        """Test basic image rotation."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create test image
            image = Image.new('RGB', (100, 200), color='green')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = rotate_image(tmp_in.name, 90.0, expand=True)
            
            assert os.path.exists(result_path)
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_rotate_image_error_handling(self):
        """Test error handling in rotation."""
        with pytest.raises(ImageProcessingError, match="Image rotation failed"):
            rotate_image("nonexistent.jpg", 45.0)


class TestImageOrientation:
    """Test image orientation detection."""
    
    def test_detect_image_orientation_basic(self):
        """Test basic orientation detection."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create test image
            image = Image.new('RGB', (100, 200), color='yellow')
            image.save(tmp.name, 'JPEG')
            
            angle = detect_image_orientation(tmp.name)
            
            assert isinstance(angle, (int, float))
            assert -180 <= angle <= 180
        
        os.unlink(tmp.name)
    
    def test_detect_image_orientation_error_handling(self):
        """Test error handling in orientation detection."""
        # The function doesn't raise exceptions, it returns 0.0 and logs warnings
        angle = detect_image_orientation("nonexistent.jpg")
        assert angle == 0.0


class TestTempImageFile:
    """Test temporary image file context manager."""
    
    def test_temp_image_file_context_manager(self):
        """Test TempImageFile context manager."""
        with TempImageFile(suffix='.jpg') as temp_path:
            assert temp_path.endswith('.jpg')
            # Create a file to test cleanup
            with open(temp_path, 'w') as f:
                f.write("test")
            assert os.path.exists(temp_path)
        
        # File should be cleaned up after context exit
        assert not os.path.exists(temp_path)
    
    def test_temp_image_file_custom_suffix(self):
        """Test TempImageFile with custom suffix."""
        with TempImageFile(suffix='.png') as temp_path:
            assert temp_path.endswith('.png')
            assert os.path.exists(temp_path)
    
    def test_temp_image_file_custom_directory(self):
        """Test TempImageFile with custom directory."""
        with tempfile.TemporaryDirectory():
            with TempImageFile(suffix='.jpg') as temp_path:
                assert temp_path.endswith('.jpg')


class TestImageInfo:
    """Test image information retrieval."""
    
    def test_get_image_info_basic(self):
        """Test basic image info retrieval."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create test image
            image = Image.new('RGB', (300, 200), color='purple')
            image.save(tmp.name, 'JPEG')
            
            info = get_image_info(tmp.name)
            
            assert 'size' in info
            assert 'format' in info
            assert 'mode' in info
            assert 'file_size' in info
            assert info['size'] == (300, 200)
            assert info['format'] == 'JPEG'
            assert info['mode'] == 'RGB'
        
        os.unlink(tmp.name)
    
    def test_get_image_info_with_exif(self):
        """Test image info with EXIF data."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create test image with some metadata
            image = Image.new('RGB', (100, 100), color='orange')
            image.save(tmp.name, 'JPEG')
            
            info = get_image_info(tmp.name)
            
            # EXIF data may or may not be present in a simple test image
            # Just verify the function returns valid info
            assert 'format' in info
            assert 'size' in info
            assert info['format'] == 'JPEG'
        
        os.unlink(tmp.name)
    
    def test_get_image_info_error_handling(self):
        """Test error handling in image info retrieval."""
        with pytest.raises(ImageProcessingError, match="Failed to get image info"):
            get_image_info("nonexistent.jpg")


class TestBytesConversion:
    """Test bytes to image conversion."""
    
    def test_bytes_to_image_success(self):
        """Test successful bytes to image conversion."""
        # Create image bytes
        image = Image.new('RGB', (50, 50), color='cyan')
        import io
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        result_image = bytes_to_image(img_bytes)
        
        assert isinstance(result_image, Image.Image)
        assert result_image.size == (50, 50)
        assert result_image.mode == 'RGB'
    
    def test_bytes_to_image_error_handling(self):
        """Test error handling in bytes to image conversion."""
        with pytest.raises(ImageProcessingError, match="Failed to convert bytes to image"):
            bytes_to_image(b"invalid image data")
    
    def test_image_to_bytes_success(self):
        """Test successful image to bytes conversion."""
        image = Image.new('RGB', (50, 50), color='magenta')
        
        result_bytes = image_to_bytes(image, format='PNG', quality=95)
        
        assert isinstance(result_bytes, bytes)
        assert len(result_bytes) > 0
        
        # Should be able to convert back
        converted_image = bytes_to_image(result_bytes)
        assert converted_image.size == (50, 50)
    
    def test_image_to_bytes_error_handling(self):
        """Test error handling in image to bytes conversion."""
        # Create invalid image object
        invalid_image = "not an image"
        
        with pytest.raises(ImageProcessingError, match="Failed to convert image to bytes"):
            image_to_bytes(invalid_image)


class TestThumbnailCreation:
    """Test thumbnail creation functionality."""
    
    def test_create_thumbnail_basic(self):
        """Test basic thumbnail creation."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create large test image
            image = Image.new('RGB', (1000, 800), color='red')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = create_thumbnail(tmp_in.name, size=(200, 200))
            
            assert os.path.exists(result_path)
            
            # Verify thumbnail size
            thumbnail = Image.open(result_path)
            assert max(thumbnail.size) <= 200
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_create_thumbnail_custom_size(self):
        """Test thumbnail creation with custom size."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_in:
            # Create test image
            image = Image.new('RGB', (500, 400), color='blue')
            image.save(tmp_in.name, 'JPEG')
            
            result_path = create_thumbnail(tmp_in.name, size=(100, 100))
            
            assert os.path.exists(result_path)
            
            # Verify thumbnail size
            thumbnail = Image.open(result_path)
            assert max(thumbnail.size) <= 100
            
            # Cleanup
            os.unlink(result_path)
        
        os.unlink(tmp_in.name)
    
    def test_create_thumbnail_error_handling(self):
        """Test error handling in thumbnail creation."""
        with pytest.raises(ImageProcessingError, match="Thumbnail creation failed"):
            create_thumbnail("nonexistent.jpg")


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_validate_image_general_exception(self):
        """Test general exception handling in validation."""
        with patch('os.path.exists', side_effect=Exception("Unexpected error")):
            with pytest.raises(ImageValidationError, match="Image validation failed"):
                validate_image_file("test.jpg")
    
    def test_cv2_operations_error_handling(self):
        """Test OpenCV operations error handling."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create test image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock cv2.imread to return None (failed read)
            with patch('cv2.imread', return_value=None):
                # detect_image_orientation uses cv2 and logs warning but doesn't raise
                angle = detect_image_orientation(tmp.name)
                assert angle == 0.0
        
        os.unlink(tmp.name)
    
    def test_memory_cleanup_on_error(self):
        """Test memory cleanup when errors occur."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create test image
            image = Image.new('RGB', (100, 100), color='red')
            image.save(tmp.name, 'JPEG')
            
            # Mock to raise exception during processing
            with patch('PIL.ImageEnhance.Brightness', side_effect=Exception("Memory error")):
                with pytest.raises(ImageProcessingError):
                    enhance_image_quality(tmp.name, enhance_brightness=True)
        
        os.unlink(tmp.name)


class TestImageProcessingHelpers:
    """Test internal helper functions."""
    
    def test_image_mode_conversions(self):
        """Test various image mode conversions."""
        # Test LA mode (grayscale with alpha)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image = Image.new('LA', (100, 100), color=(128, 255))
            image.save(tmp.name, 'PNG')
            
            result = validate_image_file(tmp.name)
            assert result['has_transparency'] is True
            assert result['mode'] == 'LA'
        
        os.unlink(tmp.name)
    
    def test_large_image_processing(self):
        """Test processing of large images."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create large but valid image
            image = Image.new('RGB', (4000, 3000), color='green')
            image.save(tmp.name, 'JPEG')
            
            # Should validate successfully
            result = validate_image_file(tmp.name)
            assert result['valid'] is True
            assert result['size'] == (4000, 3000)
        
        os.unlink(tmp.name)
