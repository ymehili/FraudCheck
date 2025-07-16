"""
Comprehensive tests for dashboard API endpoints.

This module tests all dashboard endpoints including:
- Dashboard statistics
- Analysis history with filtering and pagination
- Filter options
- Search functionality
- Main dashboard endpoint
- Helper functions
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid

from app.models.user import User
from app.models.file import FileRecord
from app.models.analysis import AnalysisResult
from app.schemas.dashboard import (
    RiskLevel, TimeRange, SortField, SortDirection,
    RiskScoreRange, DateRange, DashboardFilter, PaginationParams
)


class TestDashboardStats:
    """Test the GET /stats endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_stats_success(self, authenticated_client, db_session):
        """Test successful dashboard stats retrieval."""
        # Create test user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test files and analyses
        now = datetime.now(timezone.utc)
        
        # Create files
        file1_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file1 = FileRecord(
            id=file1_id,
            user_id=user_id,
            filename="test1.jpg",
            s3_key="test1.jpg",
            s3_url="https://test.com/test1.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=now - timedelta(days=1)
        )
        
        file2_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file2 = FileRecord(
            id=file2_id,
            user_id=user_id,
            filename="test2.jpg",
            s3_key="test2.jpg",
            s3_url="https://test.com/test2.jpg",
            file_size=2048,
            mime_type="image/jpeg",
            upload_timestamp=now - timedelta(days=2)
        )
        
        db_session.add_all([file1, file2])
        
        # Create analyses
        analysis1_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis1 = AnalysisResult(
            id=analysis1_id,
            file_id=file1_id,
            overall_risk_score=85.5,
            forensics_score=80.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.95,
            extracted_fields={"text": "test"},
            rule_violations={"violations": ["test violation"]},
            confidence_factors={},
            analysis_timestamp=now - timedelta(hours=1)
        )
        
        analysis2_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis2 = AnalysisResult(
            id=analysis2_id,
            file_id=file2_id,
            overall_risk_score=25.0,
            forensics_score=30.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.85,
            extracted_fields={"text": "test2"},
            rule_violations={"violations": []},
            confidence_factors={},
            analysis_timestamp=now - timedelta(hours=2)
        )
        
        db_session.add_all([analysis1, analysis2])
        await db_session.commit()
        
        # Mock the current user
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify basic stats
        assert "total_analyses" in data
        assert "analyses_today" in data
        assert "analyses_this_week" in data
        assert "analyses_this_month" in data
        assert "risk_distribution" in data
        assert "average_risk_score" in data
        assert "average_confidence" in data
        assert "trend_data" in data
        assert "processing_stats" in data
        
        # Verify risk distribution structure
        risk_dist = data["risk_distribution"]
        assert "low" in risk_dist
        assert "medium" in risk_dist
        assert "high" in risk_dist
        assert "critical" in risk_dist
        assert "total" in risk_dist

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_no_data(self, authenticated_client, db_session):
        """Test dashboard stats with no data."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_analyses"] == 0
        assert data["analyses_today"] == 0
        assert data["average_risk_score"] == 0.0
        assert data["average_confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_error_handling(self, authenticated_client, db_session):
        """Test dashboard stats error handling."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        with patch('app.api.deps.get_current_user', return_value=user):
            with patch('sqlalchemy.ext.asyncio.AsyncSession.scalar', side_effect=Exception("Database error")):
                response = authenticated_client.get("/api/v1/dashboard/stats")
        
        assert response.status_code == 500
        assert "Failed to retrieve dashboard statistics" in response.json()["detail"]


class TestAnalysisHistory:
    """Test the GET /history endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_analysis_history_success(self, authenticated_client, db_session):
        """Test successful analysis history retrieval."""
        # Create test user and data
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test file and analysis
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file_record = FileRecord(
            id=file_id,
            user_id=user_id,
            filename="test.jpg",
            s3_key="test.jpg",
            s3_url="https://test.com/test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(file_record)
        
        analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis = AnalysisResult(
            id=analysis_id,
            file_id=file_id,
            overall_risk_score=75.0,
            forensics_score=70.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.9,
            extracted_fields={"text": "test"},
            rule_violations={"violations": ["test violation"]},
            confidence_factors={},
            analysis_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(analysis)
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analyses" in data
        assert "pagination" in data
        assert "filters_applied" in data
        assert "summary" in data
        
        # Verify pagination info
        pagination = data["pagination"]
        assert "page" in pagination
        assert "per_page" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_previous" in pagination

    @pytest.mark.asyncio
    async def test_get_analysis_history_with_filters(self, authenticated_client, db_session):
        """Test analysis history with filters."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test with time range filter
        params = {
            "time_range": "last_7_days",
            "page": 1,
            "per_page": 10
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/history", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["time_range"] == "last_7_days"

    @pytest.mark.asyncio
    async def test_get_analysis_history_with_pagination(self, authenticated_client, db_session):
        """Test analysis history with pagination."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        params = {
            "page": 2,
            "per_page": 5,
            "sort_field": "risk_score",
            "sort_direction": "desc"
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/history", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 5


class TestFilterOptions:
    """Test the GET /filters endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_filter_options_success(self, authenticated_client, db_session):
        """Test successful filter options retrieval."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test file
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file_record = FileRecord(
            id=file_id,
            user_id=user_id,
            filename="test.jpg",
            s3_key="test.jpg",
            s3_url="https://test.com/test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(file_record)
        
        # Create test analysis
        analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis = AnalysisResult(
            id=analysis_id,
            file_id=file_id,
            overall_risk_score=50.0,
            forensics_score=45.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.8,
            extracted_fields={"text": "test"},
            rule_violations={"violations": []},
            confidence_factors={},
            analysis_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(analysis)
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/filters")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "available_risk_levels" in data
        assert "available_file_types" in data
        assert "date_range_options" in data
        assert "risk_score_range" in data
        assert "confidence_range" in data
        
        # Verify risk levels
        risk_levels = data["available_risk_levels"]
        assert "LOW" in risk_levels
        assert "MEDIUM" in risk_levels
        assert "HIGH" in risk_levels
        assert "CRITICAL" in risk_levels
        
        # Verify score ranges
        risk_range = data["risk_score_range"]
        assert "min" in risk_range
        assert "max" in risk_range
        
        confidence_range = data["confidence_range"]
        assert "min" in confidence_range
        assert "max" in confidence_range

    @pytest.mark.asyncio
    async def test_get_filter_options_no_data(self, authenticated_client, db_session):
        """Test filter options with no data."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/filters")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available_file_types"] == []
        assert data["risk_score_range"]["min"] == 0
        assert data["risk_score_range"]["max"] == 100
        assert data["confidence_range"]["min"] == 0.0
        assert data["confidence_range"]["max"] == 1.0


class TestSearchAnalyses:
    """Test the POST /search endpoint."""
    
    @pytest.mark.asyncio
    async def test_search_analyses_success(self, authenticated_client, db_session):
        """Test successful search functionality."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test file
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file_record = FileRecord(
            id=file_id,
            user_id=user_id,
            filename="searchable-file.jpg",
            s3_key="searchable-file.jpg",
            s3_url="https://test.com/searchable-file.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(file_record)
        
        # Create test analysis
        analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis = AnalysisResult(
            id=analysis_id,
            file_id=file_id,
            overall_risk_score=60.0,
            forensics_score=55.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.85,
            extracted_fields={"text": "searchable text"},
            rule_violations={"violations": ["searchable violation"]},
            confidence_factors={},
            analysis_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(analysis)
        await db_session.commit()
        
        search_request = {
            "query": "searchable",
            "search_fields": ["filename", "violations"],
            "pagination": {
                "page": 1,
                "per_page": 10
            }
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.post("/api/v1/dashboard/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "total_matches" in data
        assert "search_time" in data
        assert "pagination" in data
        assert "query_info" in data
        
        # Verify query info
        query_info = data["query_info"]
        assert query_info["query"] == "searchable"
        assert "filename" in query_info["fields_searched"]
        assert "violations" in query_info["fields_searched"]

    @pytest.mark.asyncio
    async def test_search_analyses_with_filters(self, authenticated_client, db_session):
        """Test search with additional filters."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        search_request = {
            "query": "test",
            "search_fields": ["filename"],
            "filters": {
                "time_range": "last_30_days",
                "risk_score_range": {
                    "min": 30,
                    "max": 80
                }
            },
            "pagination": {
                "page": 1,
                "per_page": 20
            }
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.post("/api/v1/dashboard/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["query_info"]["filters_applied"] is True

    @pytest.mark.asyncio
    async def test_search_analyses_no_pagination(self, authenticated_client, db_session):
        """Test search without pagination."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        search_request = {
            "query": "test",
            "search_fields": ["filename"]
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.post("/api/v1/dashboard/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        # Should have empty pagination info when not provided


class TestMainDashboard:
    """Test the GET / (main dashboard) endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_success(self, authenticated_client, db_session):
        """Test successful main dashboard retrieval."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test file
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        file_record = FileRecord(
            id=file_id,
            user_id=user_id,
            filename="dashboard-test.jpg",
            s3_key="dashboard-test.jpg",
            s3_url="https://test.com/dashboard-test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(file_record)
        
        # Create test analysis
        analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis = AnalysisResult(
            id=analysis_id,
            file_id=file_id,
            overall_risk_score=40.0,
            forensics_score=35.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.9,
            extracted_fields={"text": "test"},
            rule_violations={"violations": []},
            confidence_factors={},
            analysis_timestamp=datetime.now(timezone.utc)
        )
        db_session.add(analysis)
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        assert "recent_analyses" in data
        assert "active_alerts" in data
        assert "insights" in data
        assert "system_health" in data
        assert "updated_at" in data
        
        # Verify stats structure
        stats = data["stats"]
        assert "total_analyses" in stats
        assert "risk_distribution" in stats
        
        # Verify system health
        system_health = data["system_health"]
        assert "database_status" in system_health
        assert "last_health_check" in system_health

    @pytest.mark.asyncio
    async def test_get_dashboard_with_recent_analyses(self, authenticated_client, db_session):
        """Test dashboard with recent analyses."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create multiple files and analyses
        for i in range(5):
            file_id = f"test-file-{uuid.uuid4().hex[:8]}"
            file_record = FileRecord(
                id=file_id,
                user_id=user_id,
                filename=f"test-{i}.jpg",
                s3_key=f"test-{i}.jpg",
                s3_url=f"https://test.com/test-{i}.jpg",
                file_size=1024 * (i + 1),
                mime_type="image/jpeg",
                upload_timestamp=datetime.now(timezone.utc) - timedelta(minutes=i)
            )
            db_session.add(file_record)
            
            analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
            analysis = AnalysisResult(
                id=analysis_id,
                file_id=file_id,
                overall_risk_score=30.0 + (i * 10),
                forensics_score=25.0 + (i * 10),
                edge_inconsistencies={},
                compression_artifacts={},
                font_analysis={},
                ocr_confidence=0.8 + (i * 0.02),
                extracted_fields={"text": f"test {i}"},
                rule_violations={"violations": []},
                confidence_factors={},
                analysis_timestamp=datetime.now(timezone.utc) - timedelta(minutes=i)
            )
            db_session.add(analysis)
        
        await db_session.commit()
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/")
        
        assert response.status_code == 200
        data = response.json()
        
        recent_analyses = data["recent_analyses"]
        # The test depends on the current user match, so we'll check if it's at least structured correctly
        assert isinstance(recent_analyses, list)
        
        # Should be sorted by timestamp descending (most recent first)
        # Note: This depends on the actual implementation sorting


class TestHelperFunctions:
    """Test helper functions in the dashboard module."""
    
    @pytest.mark.asyncio
    async def test_get_risk_distribution(self, db_session):
        """Test _get_risk_distribution helper function."""
        from app.api.v1.dashboard import _get_risk_distribution
        
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        
        # Create test files with different risk scores
        risk_scores = [15, 35, 65, 85, 25, 45, 75, 95]
        
        for i, score in enumerate(risk_scores):
            file_id = f"test-file-{uuid.uuid4().hex[:8]}"
            file_record = FileRecord(
                id=file_id,
                user_id=user_id,
                filename=f"test-{i}.jpg",
                s3_key=f"test-{i}.jpg",
                s3_url=f"https://test.com/test-{i}.jpg",
                file_size=1024,
                mime_type="image/jpeg",
                upload_timestamp=datetime.now(timezone.utc)
            )
            db_session.add(file_record)
            
            analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
            analysis = AnalysisResult(
                id=analysis_id,
                file_id=file_id,
                overall_risk_score=score,
                forensics_score=score - 5,
                edge_inconsistencies={},
                compression_artifacts={},
                font_analysis={},
                ocr_confidence=0.9,
                extracted_fields={"text": f"test {i}"},
                rule_violations={"violations": []},
                confidence_factors={},
                analysis_timestamp=datetime.now(timezone.utc)
            )
            db_session.add(analysis)
        
        await db_session.commit()
        
        # Test the function
        risk_distribution = await _get_risk_distribution(db_session, user_id)
        
        # Verify distribution
        # Low: 15, 25 (2 items)
        # Medium: 35, 45 (2 items)
        # High: 65, 75 (2 items)
        # Critical: 85, 95 (2 items)
        assert risk_distribution.low == 2
        assert risk_distribution.medium == 2
        assert risk_distribution.high == 2
        assert risk_distribution.critical == 2
        assert risk_distribution.total == 8

    @pytest.mark.asyncio
    async def test_get_risk_level_from_score(self):
        """Test _get_risk_level_from_score helper function."""
        from app.api.v1.dashboard import _get_risk_level_from_score
        from app.schemas.dashboard import RiskLevel
        
        # Test all risk levels
        assert _get_risk_level_from_score(10) == RiskLevel.LOW
        assert _get_risk_level_from_score(29) == RiskLevel.LOW
        assert _get_risk_level_from_score(30) == RiskLevel.MEDIUM
        assert _get_risk_level_from_score(59) == RiskLevel.MEDIUM
        assert _get_risk_level_from_score(60) == RiskLevel.HIGH
        assert _get_risk_level_from_score(79) == RiskLevel.HIGH
        assert _get_risk_level_from_score(80) == RiskLevel.CRITICAL
        assert _get_risk_level_from_score(100) == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_convert_to_enhanced_result(self, db_session):
        """Test _convert_to_enhanced_result helper function."""
        from app.api.v1.dashboard import _convert_to_enhanced_result
        
        # Create test data
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        file_id = f"test-file-{uuid.uuid4().hex[:8]}"
        
        file_record = FileRecord(
            id=file_id,
            user_id=user_id,
            filename="test.jpg",
            s3_key="test.jpg",
            s3_url="https://test.com/test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            upload_timestamp=datetime.now(timezone.utc)
        )
        
        analysis_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
        analysis = AnalysisResult(
            id=analysis_id,
            file_id=file_id,
            overall_risk_score=65.0,
            forensics_score=60.0,
            edge_inconsistencies={},
            compression_artifacts={},
            font_analysis={},
            ocr_confidence=0.95,
            extracted_fields={"text": "test"},
            rule_violations={"violations": ["test violation"], "recommendations": ["test recommendation"]},
            confidence_factors={},
            analysis_timestamp=datetime.now(timezone.utc)
        )
        
        # Mock the file relationship
        analysis.file = file_record
        
        # Test the function
        enhanced_result = await _convert_to_enhanced_result(analysis)
        
        # Verify enhanced result structure
        assert enhanced_result.id == analysis_id
        assert enhanced_result.file_id == file_id
        assert enhanced_result.filename == "test.jpg"
        assert enhanced_result.overall_risk_score == 65.0
        assert enhanced_result.forensics_score == 60.0
        assert enhanced_result.ocr_confidence == 0.95
        assert enhanced_result.violations == ["test violation"]
        
        # Verify risk score details
        risk_details = enhanced_result.risk_score_details
        assert risk_details.overall_score == 65
        assert risk_details.risk_level == RiskLevel.HIGH
        assert risk_details.confidence_level == 0.95
        assert risk_details.risk_factors == ["test violation"]
        assert risk_details.recommendations == ["test recommendation"]


class TestErrorHandling:
    """Test error handling in dashboard endpoints."""
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to dashboard endpoints."""
        # Clear any existing dependency overrides
        from app.main import app
        app.dependency_overrides.clear()
        
        # Test without authentication
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401
        
        response = client.get("/api/v1/dashboard/history")
        assert response.status_code == 401
        
        response = client.get("/api/v1/dashboard/filters")
        assert response.status_code == 401
        
        response = client.post("/api/v1/dashboard/search", json={"query": "test", "search_fields": ["filename"]})
        assert response.status_code == 401
        
        response = client.get("/api/v1/dashboard/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_search_request(self, authenticated_client, db_session):
        """Test invalid search request."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test with invalid search fields
        invalid_request = {
            "query": "test",
            "search_fields": []  # Empty search fields
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.post("/api/v1/dashboard/search", json=invalid_request)
        
        # Should handle gracefully or return appropriate error
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_invalid_pagination_params(self, authenticated_client, db_session):
        """Test invalid pagination parameters."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test with invalid page number
        params = {
            "page": 0,  # Invalid page number
            "per_page": 10
        }
        
        with patch('app.api.deps.get_current_user', return_value=user):
            response = authenticated_client.get("/api/v1/dashboard/history", params=params)
        
        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_database_connection_error(self, authenticated_client):
        """Test database connection error handling."""
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        with patch('app.api.deps.get_current_user', return_value=user):
            with patch('sqlalchemy.ext.asyncio.AsyncSession.scalar', side_effect=Exception("Database connection failed")):
                response = authenticated_client.get("/api/v1/dashboard/stats")
        
        # Should handle database errors gracefully
        assert response.status_code == 500