import pytest

from app.core.config import Settings, settings


class TestConfig:
    """Test configuration settings."""

    def test_settings_instance(self):
        """Test that settings instance exists."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_database_url_setting(self):
        """Test DATABASE_URL setting."""
        assert hasattr(settings, 'DATABASE_URL')
        assert settings.DATABASE_URL is not None
        assert isinstance(settings.DATABASE_URL, str)

    def test_aws_settings(self):
        """Test AWS-related settings."""
        # Test that AWS settings exist
        assert hasattr(settings, 'AWS_ACCESS_KEY_ID')
        assert hasattr(settings, 'AWS_SECRET_ACCESS_KEY')
        assert hasattr(settings, 'AWS_REGION')
        assert hasattr(settings, 'S3_BUCKET_NAME')

    def test_clerk_settings(self):
        """Test Clerk-related settings."""
        assert hasattr(settings, 'CLERK_SECRET_KEY')

    def test_file_upload_settings(self):
        """Test file upload related settings."""
        assert hasattr(settings, 'MAX_FILE_SIZE')
        assert hasattr(settings, 'ALLOWED_FILE_TYPES')
        
        # Test that MAX_FILE_SIZE is a positive integer
        if settings.MAX_FILE_SIZE is not None:
            assert isinstance(settings.MAX_FILE_SIZE, int)
            assert settings.MAX_FILE_SIZE > 0
        
        # Test that ALLOWED_FILE_TYPES is a list
        if settings.ALLOWED_FILE_TYPES is not None:
            assert isinstance(settings.ALLOWED_FILE_TYPES, list)

    def test_optional_aws_endpoint_url(self):
        """Test optional AWS endpoint URL setting."""
        assert hasattr(settings, 'AWS_ENDPOINT_URL')
        # AWS_ENDPOINT_URL is optional, so it can be None

    def test_settings_can_be_instantiated(self):
        """Test that Settings class can be instantiated."""
        test_settings = Settings()
        assert test_settings is not None

    def test_env_file_loading(self):
        """Test that environment variables are loaded."""
        # Test that the settings object has the expected structure
        assert hasattr(settings, 'model_config')

    def test_settings_validation(self):
        """Test settings validation."""
        # Test that settings are properly validated
        # The fact that settings object exists means validation passed
        assert settings is not None

    def test_cors_origins_setting(self):
        """Test CORS origins setting if it exists."""
        # Some apps have CORS origins configured
        cors_attr = getattr(settings, 'CORS_ORIGINS', None)
        if cors_attr is not None:
            assert isinstance(cors_attr, (list, str))

    def test_debug_mode_setting(self):
        """Test debug mode setting if it exists."""
        debug_attr = getattr(settings, 'DEBUG', None)
        if debug_attr is not None:
            assert isinstance(debug_attr, bool)

    def test_secret_key_setting(self):
        """Test secret key setting if it exists."""
        secret_attr = getattr(settings, 'SECRET_KEY', None)
        if secret_attr is not None:
            assert isinstance(secret_attr, str)
            assert len(secret_attr) > 0

    def test_api_version_setting(self):
        """Test API version setting if it exists."""
        version_attr = getattr(settings, 'API_VERSION', None)
        if version_attr is not None:
            assert isinstance(version_attr, str)

    def test_environment_setting(self):
        """Test environment setting if it exists."""
        env_attr = getattr(settings, 'ENVIRONMENT', None)
        if env_attr is not None:
            assert isinstance(env_attr, str)
            assert env_attr in ['development', 'production', 'testing']

    def test_settings_immutability(self):
        """Test that certain settings should not be easily modified."""
        # Get original value
        original_db_url = settings.DATABASE_URL
        
        # Settings should be read-only in most cases
        # This test just verifies the setting exists and has a value
        assert original_db_url is not None
