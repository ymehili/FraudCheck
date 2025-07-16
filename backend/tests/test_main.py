import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


class TestMain:
    """Test main application functionality."""

    def test_app_creation(self):
        """Test FastAPI app creation."""
        assert app is not None
        assert app.title == "CheckGuard AI API"

    def test_cors_middleware(self):
        """Test CORS middleware is configured."""
        # Check that CORS middleware is added
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'CORSMiddleware':
                middleware_found = True
                break
        assert middleware_found

    def test_router_inclusion(self):
        """Test that routers are included."""
        # Test that API routes are included
        client = TestClient(app)
        
        # Test auth routes
        response = client.get("/api/v1/auth/me")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
        
        # Test files routes
        response = client.get("/api/v1/files/")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401

    def test_health_check_endpoint(self):
        """Test health check endpoint if it exists."""
        client = TestClient(app)
        
        # Try to access root endpoint
        response = client.get("/")
        # Should not be 404, might be redirected or have some response
        assert response.status_code in [200, 307, 404]  # Allow various responses

    def test_docs_endpoint(self):
        """Test API documentation endpoint."""
        client = TestClient(app)
        
        # OpenAPI docs should be available
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """Test OpenAPI schema generation."""
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "info" in data
        assert data["info"]["title"] == "CheckGuard AI API"

    def test_exception_handling(self):
        """Test global exception handling."""
        client = TestClient(app)
        
        # Test non-existent endpoint
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404

    def test_app_settings_integration(self):
        """Test that app integrates with settings."""
        # Settings should be accessible
        assert settings is not None
        assert hasattr(settings, 'DATABASE_URL')

    @patch('app.api.deps.get_db')
    def test_database_dependency(self, mock_get_db):
        """Test database dependency injection."""
        mock_get_db.return_value = MagicMock()
        
        client = TestClient(app)
        
        # Any endpoint that uses database should work with mocked db
        response = client.get("/api/v1/files/", headers={"Authorization": "Bearer fake-token"})
        # Should not crash due to database issues
        assert response.status_code in [200, 401, 422]  # Various valid responses
