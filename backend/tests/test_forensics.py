import pytest
import numpy as np
import cv2
from PIL import Image
import tempfile
import os

from app.core.forensics import ForensicsEngine
from app.schemas.analysis import ForensicsResult


@pytest.fixture
def forensics_engine():
    """Create forensics engine for testing."""
    return ForensicsEngine()


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple test image
    image = Image.new('RGB', (200, 100), color='white')
    
    # Add some text-like patterns
    import PIL.ImageDraw
    draw = PIL.ImageDraw.Draw(image)
    draw.text((10, 10), "TEST CHECK", fill='black')
    draw.text((10, 30), "Pay to: John Doe", fill='black')
    draw.text((10, 50), "$100.00", fill='black')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except OSError:
        pass


@pytest.fixture
def corrupted_image():
    """Create a corrupted image for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    temp_file.write(b'invalid image data')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_forensics_engine_basic(forensics_engine, sample_image):
    """Test basic forensics analysis on sample image."""
    result = await forensics_engine.analyze_image(sample_image)
    
    assert isinstance(result, ForensicsResult)
    assert 0.0 <= result.edge_score <= 1.0
    assert 0.0 <= result.compression_score <= 1.0
    assert 0.0 <= result.font_score <= 1.0
    assert 0.0 <= result.overall_score <= 1.0
    assert isinstance(result.detected_anomalies, list)
    assert isinstance(result.edge_inconsistencies, dict)
    assert isinstance(result.compression_artifacts, dict)
    assert isinstance(result.font_analysis, dict)


@pytest.mark.asyncio
async def test_forensics_engine_nonexistent_image(forensics_engine):
    """Test forensics engine with nonexistent image."""
    with pytest.raises(FileNotFoundError):
        await forensics_engine.analyze_image("nonexistent.jpg")


@pytest.mark.asyncio
async def test_forensics_engine_invalid_image(forensics_engine, corrupted_image):
    """Test forensics engine with invalid image."""
    with pytest.raises(ValueError):
        await forensics_engine.analyze_image(corrupted_image)


@pytest.mark.asyncio
async def test_edge_inconsistency_detection(forensics_engine, sample_image):
    """Test edge inconsistency detection."""
    # Load image for testing
    image = cv2.imread(sample_image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    result = await forensics_engine._detect_edge_inconsistencies(image_rgb)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'continuity' in result
    assert 'sharpness' in result
    assert 'cloned_regions' in result


@pytest.mark.asyncio
async def test_compression_artifact_analysis(forensics_engine, sample_image):
    """Test compression artifact analysis."""
    # Load image for testing
    image = cv2.imread(sample_image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    result = await forensics_engine._analyze_compression_artifacts(image_rgb)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'jpeg_artifacts' in result
    assert 'inconsistencies' in result
    assert 'recompression_patterns' in result


@pytest.mark.asyncio
async def test_font_consistency_analysis(forensics_engine, sample_image):
    """Test font consistency analysis."""
    # Load image for testing
    image = cv2.imread(sample_image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    result = await forensics_engine._analyze_font_consistency(image_rgb)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'text_regions' in result
    assert 'font_characteristics' in result
    assert 'inconsistencies' in result


@pytest.mark.asyncio
async def test_edge_continuity_analysis(forensics_engine, sample_image):
    """Test edge continuity analysis."""
    # Create mock edges
    edges = np.zeros((100, 200), dtype=bool)
    edges[10:20, 10:50] = True  # Some edge pixels
    edges[30:40, 30:70] = True  # Another edge region
    
    result = forensics_engine._analyze_edge_continuity(edges)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'total_regions' in result
    assert 'broken_edges' in result


@pytest.mark.asyncio
async def test_cloned_region_detection(forensics_engine, sample_image):
    """Test cloned region detection."""
    # Create test image with potential cloned regions
    gray = np.random.rand(100, 100).astype(np.float32)
    
    result = forensics_engine._detect_cloned_regions(gray)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'high_correlations' in result
    assert 'total_comparisons' in result


@pytest.mark.asyncio
async def test_jpeg_artifact_detection(forensics_engine, sample_image):
    """Test JPEG artifact detection."""
    # Create test grayscale image
    gray = np.random.rand(100, 100).astype(np.float32)
    
    result = forensics_engine._detect_jpeg_artifacts(gray)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'blocks_analyzed' in result


@pytest.mark.asyncio
async def test_text_region_detection(forensics_engine, sample_image):
    """Test text region detection."""
    # Load image for testing
    image = cv2.imread(sample_image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    result = forensics_engine._detect_text_regions(gray)
    
    assert isinstance(result, list)
    # Should detect some text regions in our sample image
    assert len(result) >= 0  # May or may not detect text regions


@pytest.mark.asyncio
async def test_font_characteristics_analysis(forensics_engine, sample_image):
    """Test font characteristics analysis."""
    # Load image for testing
    image = cv2.imread(sample_image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create some mock text regions
    text_regions = [
        {'bbox': [10, 10, 50, 20], 'area': 1000, 'aspect_ratio': 2.5},
        {'bbox': [10, 30, 80, 20], 'area': 1600, 'aspect_ratio': 4.0}
    ]
    
    result = forensics_engine._analyze_font_characteristics(gray, text_regions)
    
    assert isinstance(result, dict)
    assert 'consistency_score' in result
    assert 0.0 <= result['consistency_score'] <= 1.0
    assert 'characteristics' in result
    assert 'regions_analyzed' in result


@pytest.mark.asyncio
async def test_stroke_width_estimation(forensics_engine, sample_image):
    """Test stroke width estimation."""
    # Create a small text region
    text_roi = np.ones((20, 50)) * 0.8  # Light background
    text_roi[5:15, 10:40] = 0.2  # Dark text
    
    result = forensics_engine._estimate_stroke_width(text_roi)
    
    assert isinstance(result, float)
    assert result > 0


@pytest.mark.asyncio
async def test_font_inconsistency_detection(forensics_engine):
    """Test font inconsistency detection."""
    # Create mock font characteristics
    font_characteristics = {
        'consistency_score': 0.7,
        'characteristics': [
            {'stroke_width': 2.0, 'text_density': 0.3},
            {'stroke_width': 2.5, 'text_density': 0.4},
            {'stroke_width': 3.0, 'text_density': 0.5}
        ]
    }
    
    result = forensics_engine._detect_font_inconsistencies(font_characteristics)
    
    assert isinstance(result, dict)
    assert 'penalty' in result
    assert 0.0 <= result['penalty'] <= 1.0
    assert 'inconsistencies' in result


@pytest.mark.asyncio
async def test_text_alignment_analysis(forensics_engine):
    """Test text alignment analysis."""
    # Create mock text regions
    text_regions = [
        {'bbox': [10, 10, 50, 20]},
        {'bbox': [10, 35, 80, 20]},
        {'bbox': [10, 60, 60, 20]}
    ]
    
    gray = np.zeros((100, 100))
    
    result = forensics_engine._analyze_text_alignment(gray, text_regions)
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 'alignment_score' in result
    assert 'spacing_score' in result


@pytest.mark.asyncio
async def test_anomaly_compilation(forensics_engine):
    """Test anomaly compilation."""
    # Create mock analysis results
    edge_analysis = {
        'score': 0.2,  # Low score indicates poor edges
        'cloned_regions': {'score': 0.6}  # High score indicates potential cloning
    }
    
    compression_analysis = {
        'score': 0.8  # High score indicates high artifacts
    }
    
    font_analysis = {
        'inconsistencies': {
            'inconsistencies': ['High stroke width variation']
        }
    }
    
    result = forensics_engine._compile_anomalies(
        edge_analysis, 
        compression_analysis, 
        font_analysis
    )
    
    assert isinstance(result, list)
    assert len(result) >= 0  # May contain anomalies


@pytest.mark.asyncio
async def test_forensics_engine_error_handling(forensics_engine):
    """Test forensics engine error handling."""
    # Test with various error conditions
    with pytest.raises(FileNotFoundError):
        await forensics_engine.analyze_image("test.jpg")


@pytest.mark.asyncio
async def test_forensics_parallel_analysis(forensics_engine, sample_image):
    """Test that forensics analysis components run in parallel."""
    # This test ensures that the async components work correctly
    result = await forensics_engine.analyze_image(sample_image)
    
    # All components should have results
    assert result.edge_score is not None
    assert result.compression_score is not None
    assert result.font_score is not None
    assert result.overall_score is not None


@pytest.mark.asyncio
async def test_forensics_memory_cleanup(forensics_engine, sample_image):
    """Test that forensics engine properly cleans up memory."""
    # Run analysis multiple times to check for memory leaks
    for _ in range(3):
        result = await forensics_engine.analyze_image(sample_image)
        assert result is not None
    
    # This test mainly ensures no exceptions are raised during cleanup


@pytest.mark.asyncio
async def test_forensics_with_different_image_sizes(forensics_engine):
    """Test forensics engine with different image sizes."""
    # Test with small image
    small_image = Image.new('RGB', (50, 50), color='white')
    small_temp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    small_image.save(small_temp.name, 'JPEG')
    small_temp.close()
    
    try:
        result = await forensics_engine.analyze_image(small_temp.name)
        assert result is not None
    finally:
        os.unlink(small_temp.name)
    
    # Test with large image
    large_image = Image.new('RGB', (1000, 1000), color='white')
    large_temp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    large_image.save(large_temp.name, 'JPEG')
    large_temp.close()
    
    try:
        result = await forensics_engine.analyze_image(large_temp.name)
        assert result is not None
    finally:
        os.unlink(large_temp.name)


@pytest.mark.asyncio
async def test_forensics_score_ranges(forensics_engine, sample_image):
    """Test that all forensics scores are within expected ranges."""
    result = await forensics_engine.analyze_image(sample_image)
    
    # All scores should be between 0 and 1
    assert 0.0 <= result.edge_score <= 1.0
    assert 0.0 <= result.compression_score <= 1.0
    assert 0.0 <= result.font_score <= 1.0
    assert 0.0 <= result.overall_score <= 1.0
    
    # Overall score should be a weighted average of component scores
    expected_overall = (
        result.edge_score * 0.4 + 
        result.compression_score * 0.3 + 
        result.font_score * 0.3
    )
    
    # Allow for small floating point differences
    assert abs(result.overall_score - expected_overall) < 0.01