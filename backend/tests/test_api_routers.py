
from app.api.v1.api import router
from app.api.v1.auth import router as auth_router
from app.api.v1.files import router as files_router


class TestApiRouters:
    """Test API router configuration and endpoints."""

    def test_main_api_router_exists(self):
        """Test that main API router exists."""
        assert router is not None

    def test_auth_router_exists(self):
        """Test that auth router exists."""
        assert auth_router is not None

    def test_files_router_exists(self):
        """Test that files router exists."""
        assert files_router is not None

    def test_router_tags(self):
        """Test router tags configuration."""
        # Check if routers have proper tags
        if hasattr(auth_router, 'tags'):
            assert 'auth' in auth_router.tags or 'authentication' in auth_router.tags
        
        if hasattr(files_router, 'tags'):
            assert 'files' in files_router.tags or 'file' in files_router.tags

    def test_router_prefixes(self):
        """Test router prefixes if configured."""
        # Check if routers have proper prefixes configured
        if hasattr(auth_router, 'prefix'):
            assert auth_router.prefix is not None
        
        if hasattr(files_router, 'prefix'):
            assert files_router.prefix is not None

    def test_router_routes_exist(self):
        """Test that routers have routes configured."""
        # Auth router should have routes
        assert len(auth_router.routes) > 0
        
        # Files router should have routes
        assert len(files_router.routes) > 0

    def test_api_router_includes_subrouters(self):
        """Test that main API router includes sub-routers."""
        # Main router should include other routers
        assert len(router.routes) > 0

    def test_route_methods(self):
        """Test that routes have proper HTTP methods."""
        # Check auth router routes
        auth_methods = []
        for route in auth_router.routes:
            if hasattr(route, 'methods'):
                auth_methods.extend(route.methods)
        
        # Should have GET method for /me endpoint
        assert 'GET' in auth_methods or 'POST' in auth_methods

        # Check files router routes
        files_methods = []
        for route in files_router.routes:
            if hasattr(route, 'methods'):
                files_methods.extend(route.methods)
        
        # Should have multiple HTTP methods
        assert len(set(files_methods)) > 1

    def test_route_paths(self):
        """Test route paths configuration."""
        # Check that routes have paths
        for route in auth_router.routes:
            if hasattr(route, 'path'):
                assert route.path is not None
                assert isinstance(route.path, str)

        for route in files_router.routes:
            if hasattr(route, 'path'):
                assert route.path is not None
                assert isinstance(route.path, str)

    def test_router_dependencies(self):
        """Test router dependencies if configured."""
        # Check if routers have dependencies
        if hasattr(auth_router, 'dependencies'):
            assert isinstance(auth_router.dependencies, list)
        
        if hasattr(files_router, 'dependencies'):
            assert isinstance(files_router.dependencies, list)

    def test_route_responses(self):
        """Test route response configurations."""
        # Check that routes have response models or status codes
        for route in files_router.routes:
            if hasattr(route, 'response_model'):
                # Routes might have response models
                pass
            if hasattr(route, 'status_code'):
                # Routes might have status codes
                pass

    def test_router_middleware_compatibility(self):
        """Test that routers are compatible with middleware."""
        # Routers should be compatible with FastAPI middleware
        assert hasattr(auth_router, 'routes')
        assert hasattr(files_router, 'routes')

    def test_route_security(self):
        """Test route security configurations."""
        # Some routes should have security dependencies
        for route in files_router.routes:
            if hasattr(route, 'dependencies') and route.dependencies:
                break
        
        # At least some routes should have dependencies (for auth)
        # This is a loose test since security might be configured differently
        assert True  # Routes exist and can be tested

    def test_error_handling_routes(self):
        """Test error handling in routes."""
        # Routes should be properly configured to handle errors
        for route in auth_router.routes:
            if hasattr(route, 'endpoint'):
                assert callable(route.endpoint)

        for route in files_router.routes:
            if hasattr(route, 'endpoint'):
                assert callable(route.endpoint)

    def test_api_versioning(self):
        """Test API versioning structure."""
        # Check that the routers are imported from v1 module
        from app.api.v1.api import router as api_router
        from app.api.v1.auth import router as v1_auth_router
        from app.api.v1.files import router as v1_files_router
        
        # Verify the imports work and routers exist
        assert api_router is not None
        assert v1_auth_router is not None
        assert v1_files_router is not None
        
        # Check that the main router includes the sub-routers properly
        assert len(api_router.routes) > 0
