"""
Dashboard API endpoints for FraudCheck AI.

This module provides comprehensive dashboard functionality including:
- Dashboard statistics and overview
- Analysis history with filtering and pagination
- Risk distribution analytics
- Trend analysis
- Export functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_, case
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import json
from pathlib import Path

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...models.search_index import SearchIndex
from ...schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    EnhancedAnalysisResult,
    DashboardFilter,
    PaginationParams,
    FilterOptionsResponse,
    RiskDistribution,
    TrendDataPoint,
    RiskLevel,
    TimeRange,
    SortField,
    SortDirection,
    CategoryScore,
    RiskScoreDetails,
    DashboardSearchRequest,
    DashboardSearchResponse
)
from ..deps import get_current_user
from ...utils.cache import cached

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)


@cached(ttl_seconds=180)  # Cache for 3 minutes
async def _get_dashboard_stats_cached(user_id: str, db: AsyncSession) -> DashboardStats:
    """Cached implementation of dashboard stats retrieval."""
    try:
        # Calculate time boundaries once
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        # Single optimized query for all statistics
        stats_query = (
            select(
                func.count(AnalysisResult.id).label('total_analyses'),
                func.sum(
                    case(
                        (AnalysisResult.analysis_timestamp >= today_start, 1),
                        else_=0
                    )
                ).label('analyses_today'),
                func.sum(
                    case(
                        (AnalysisResult.analysis_timestamp >= week_start, 1),
                        else_=0
                    )
                ).label('analyses_this_week'),
                func.sum(
                    case(
                        (AnalysisResult.analysis_timestamp >= month_start, 1),
                        else_=0
                    )
                ).label('analyses_this_month'),
                func.avg(AnalysisResult.overall_risk_score).label('avg_risk_score'),
                func.avg(AnalysisResult.ocr_confidence).label('avg_confidence'),
                # Risk distribution in single query
                func.sum(
                    case(
                        (AnalysisResult.overall_risk_score < 30, 1),
                        else_=0
                    )
                ).label('risk_low'),
                func.sum(
                    case(
                        (and_(AnalysisResult.overall_risk_score >= 30, AnalysisResult.overall_risk_score < 60), 1),
                        else_=0
                    )
                ).label('risk_medium'),
                func.sum(
                    case(
                        (and_(AnalysisResult.overall_risk_score >= 60, AnalysisResult.overall_risk_score < 80), 1),
                        else_=0
                    )
                ).label('risk_high'),
                func.sum(
                    case(
                        (AnalysisResult.overall_risk_score >= 80, 1),
                        else_=0
                    )
                ).label('risk_critical')
            )
            .select_from(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == user_id)
        )
        
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()
        
        if stats_row:
            total_analyses = stats_row.total_analyses or 0
            analyses_today = stats_row.analyses_today or 0
            analyses_this_week = stats_row.analyses_this_week or 0
            analyses_this_month = stats_row.analyses_this_month or 0
            avg_risk_score = stats_row.avg_risk_score
            avg_confidence = stats_row.avg_confidence
            
            # Build risk distribution from single query
            risk_distribution = RiskDistribution(
                low=stats_row.risk_low or 0,
                medium=stats_row.risk_medium or 0,
                high=stats_row.risk_high or 0,
                critical=stats_row.risk_critical or 0,
                total=total_analyses
            )
        else:
            total_analyses = analyses_today = analyses_this_week = analyses_this_month = 0
            avg_risk_score = avg_confidence = None
            risk_distribution = RiskDistribution(low=0, medium=0, high=0, critical=0, total=0)
        
        # Get most common violations
        most_common_violations = await _get_most_common_violations(db, user_id)
        
        # Get trend data for the last 30 days using optimized single query
        trend_data = await _get_trend_data_optimized(db, user_id, days=30)
        
        # Get processing statistics
        processing_stats = await _get_processing_stats(db, user_id)
        
        return DashboardStats(
            total_analyses=total_analyses,
            analyses_today=analyses_today,
            analyses_this_week=analyses_this_week,
            analyses_this_month=analyses_this_month,
            risk_distribution=risk_distribution,
            average_risk_score=float(avg_risk_score) if avg_risk_score else 0.0,
            average_confidence=float(avg_confidence) if avg_confidence else 0.0,
            most_common_violations=most_common_violations,
            trend_data=trend_data,
            processing_stats=processing_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard statistics"
        )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics.
    
    Returns overview statistics including:
    - Total analyses count
    - Risk distribution
    - Trend data
    - Processing statistics
    """
    return await _get_dashboard_stats_cached(current_user.id, db)


@router.get("/history")
async def get_analysis_history(
    page: int = 1,
    size: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    max_risk_score: Optional[float] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated analysis history with filtering.
    
    Supports filtering by:
    - Date range (start_date, end_date)
    - Risk score range (min_risk_score, max_risk_score)
    - Status
    """
    try:
        
        # Apply simple filters
        query_conditions = [FileRecord.user_id == current_user.id]
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query_conditions.append(AnalysisResult.analysis_timestamp >= start_dt)
            except ValueError:
                pass  # Ignore invalid date format
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query_conditions.append(AnalysisResult.analysis_timestamp <= end_dt)
            except ValueError:
                pass  # Ignore invalid date format
        
        if min_risk_score is not None:
            query_conditions.append(AnalysisResult.overall_risk_score >= min_risk_score)
        
        if max_risk_score is not None:
            query_conditions.append(AnalysisResult.overall_risk_score <= max_risk_score)
        
        if status and status.lower() != 'all':
            # For now, all analyses have 'completed' status
            # This can be extended when status tracking is implemented
            pass
        
        # Build filtered query
        filtered_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(and_(*query_conditions))
            .options(joinedload(AnalysisResult.file))
            .order_by(desc(AnalysisResult.analysis_timestamp))
        )
        
        # Get total count for pagination
        count_query = (
            select(func.count(AnalysisResult.id))
            .select_from(AnalysisResult)
            .join(FileRecord)
            .where(and_(*query_conditions))
        )
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        offset = (page - 1) * size
        paginated_query = filtered_query.offset(offset).limit(size)
        
        # Execute query
        result = await db.execute(paginated_query)
        analyses = result.scalars().all()
        
        # Convert to simple history items that match frontend expectations
        history_items = []
        for analysis in analyses:
            violations = analysis.rule_violations.get('violations', []) if analysis.rule_violations else []
            
            history_item = {
                'analysis_id': analysis.id,
                'file_id': analysis.file_id,
                'filename': analysis.file.filename,
                'timestamp': analysis.analysis_timestamp.isoformat(),
                'created_at': analysis.analysis_timestamp.isoformat(),
                'overall_risk_score': int(analysis.overall_risk_score),
                'confidence': analysis.ocr_confidence,
                'status': 'completed',  # For now, assume all are completed
                'violations_count': len(violations),
                'primary_violations': violations[:3],  # First 3 violations
                'processing_time': None  # TODO: Add processing time tracking
            }
            history_items.append(history_item)
        
        # Calculate pagination info
        total_pages = ((total_count or 0) + size - 1) // size
        
        # Return a paginated response that matches frontend expectations
        return {
            'items': history_items,
            'total': total_count or 0,
            'page': page,
            'size': size,
            'pages': total_pages
        }
        
    except Exception as e:
        logger.error(f"Failed to get analysis history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analysis history"
        )


@router.get("/filters", response_model=FilterOptionsResponse)
async def get_filter_options(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available filter options for the dashboard.
    
    Returns available options for:
    - Risk levels
    - File types
    - Date ranges
    - Score ranges
    """
    try:
        # Get available file types
        file_types_result = await db.execute(
            select(func.distinct(FileRecord.mime_type))
            .where(FileRecord.user_id == current_user.id)
        )
        available_file_types = [row[0] for row in file_types_result.fetchall() or []]
        
        # Get risk score range
        risk_score_result = await db.execute(
            select(
                func.min(AnalysisResult.overall_risk_score),
                func.max(AnalysisResult.overall_risk_score)
            )
            .where(AnalysisResult.file.has(FileRecord.user_id == current_user.id))
        )
        result = risk_score_result.first()
        min_risk, max_risk = result if result else (None, None)
        
        # Get confidence range
        confidence_result = await db.execute(
            select(
                func.min(AnalysisResult.ocr_confidence),
                func.max(AnalysisResult.ocr_confidence)
            )
            .where(AnalysisResult.file.has(FileRecord.user_id == current_user.id))
        )
        result = confidence_result.first()
        min_confidence, max_confidence = result if result else (None, None)
        
        return FilterOptionsResponse(
            available_risk_levels=list(RiskLevel),
            available_file_types=available_file_types,
            date_range_options=list(TimeRange),
            risk_score_range={
                'min': int(min_risk) if min_risk else 0,
                'max': int(max_risk) if max_risk else 100
            },
            confidence_range={
                'min': float(min_confidence) if min_confidence else 0.0,
                'max': float(max_confidence) if max_confidence else 1.0
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get filter options: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve filter options"
        )


@router.post("/search", response_model=DashboardSearchResponse)
async def search_analyses(
    search_request: DashboardSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search analyses with full-text search capabilities.
    
    Supports searching across:
    - Filenames
    - Violations
    - Risk factors
    - OCR extracted text
    """
    try:
        start_time = datetime.utcnow()
        
        # Build optimized search query using search index
        search_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .join(SearchIndex, AnalysisResult.id == SearchIndex.analysis_id)
            .where(FileRecord.user_id == current_user.id)
            .options(joinedload(AnalysisResult.file))
        )
        
        # Apply text search using indexed columns
        search_conditions = []
        query_term = f"%{search_request.query}%"
        
        if 'filename' in search_request.search_fields:
            search_conditions.append(SearchIndex.filename.ilike(query_term))
        
        if 'violations' in search_request.search_fields:
            search_conditions.append(SearchIndex.violations_text.ilike(query_term))
        
        if 'risk_factors' in search_request.search_fields:
            search_conditions.append(SearchIndex.risk_factors_text.ilike(query_term))
            
        if 'ocr_text' in search_request.search_fields:
            search_conditions.append(SearchIndex.ocr_text.ilike(query_term))
        
        # Fallback to combined search if no specific fields or for comprehensive search
        if not search_conditions or len(search_request.search_fields) > 2:
            search_conditions.append(SearchIndex.search_text.ilike(query_term))
        
        if search_conditions:
            search_query = search_query.where(or_(*search_conditions))
        
        # Apply additional filters
        if search_request.filters:
            search_query = await _apply_filters(search_query, search_request.filters)
        
        # Apply sorting and pagination
        if search_request.pagination:
            search_query = await _apply_sorting(search_query, search_request.pagination)
            
            # Get total count
            count_query = select(func.count()).select_from(search_query.subquery())
            total_matches = await db.scalar(count_query)
            
            # Apply pagination
            offset = (search_request.pagination.page - 1) * search_request.pagination.per_page
            search_query = search_query.offset(offset).limit(search_request.pagination.per_page)
        else:
            # Get total count without pagination
            count_query = select(func.count()).select_from(search_query.subquery())
            total_matches = await db.scalar(count_query)
        
        # Execute search
        result = await db.execute(search_query)
        analyses = result.scalars().all()
        
        # Convert to enhanced results
        enhanced_results = []
        for analysis in analyses:
            enhanced_result = await _convert_to_enhanced_result(analysis)
            enhanced_results.append(enhanced_result)
        
        # Calculate search time
        search_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Build pagination info
        pagination_info = {}
        if search_request.pagination:
            total_pages = ((total_matches or 0) + search_request.pagination.per_page - 1) // search_request.pagination.per_page
            pagination_info = {
                'page': search_request.pagination.page,
                'per_page': search_request.pagination.per_page,
                'total_items': total_matches or 0,
                'total_pages': total_pages,
                'has_next': search_request.pagination.page < total_pages,
                'has_previous': search_request.pagination.page > 1
            }
        
        return DashboardSearchResponse(
            results=enhanced_results,
            total_matches=total_matches or 0,
            search_time=search_time,
            pagination=pagination_info,
            query_info={
                'query': search_request.query,
                'fields_searched': search_request.search_fields,
                'filters_applied': search_request.filters is not None
            }
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Search failed"
        )


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete dashboard data.
    
    Returns comprehensive dashboard information including:
    - Statistics
    - Recent analyses
    - System health
    """
    try:
        # Get dashboard stats
        stats = await get_dashboard_stats(current_user, db)
        
        # Get recent analyses (last 10)
        recent_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == current_user.id)
            .options(joinedload(AnalysisResult.file))
            .order_by(desc(AnalysisResult.analysis_timestamp))
            .limit(10)
        )
        
        recent_result = await db.execute(recent_query)
        recent_analyses_raw = recent_result.scalars().all()
        
        recent_analyses = []
        for analysis in recent_analyses_raw:
            enhanced_analysis = await _convert_to_enhanced_result(analysis)
            recent_analyses.append(enhanced_analysis)
        
        # System health information
        system_health = await _get_system_health(db)
        
        return DashboardResponse(
            stats=stats,
            recent_analyses=recent_analyses,
            active_alerts=[],  # TODO: Implement alerts system
            insights=[],       # TODO: Implement insights system
            system_health=system_health,
            updated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard"
        )


# Helper functions
async def _get_risk_distribution(db: AsyncSession, user_id: str) -> RiskDistribution:
    """Calculate risk distribution for user's analyses using optimized single query."""
    try:
        # Single optimized query using conditional aggregation with correct thresholds
        risk_query = (
            select(
                func.count(AnalysisResult.id).label('total'),
                func.sum(
                    case((AnalysisResult.overall_risk_score < 30, 1), else_=0)
                ).label('low'),
                func.sum(
                    case(
                        (and_(AnalysisResult.overall_risk_score >= 30, AnalysisResult.overall_risk_score < 60), 1),
                        else_=0
                    )
                ).label('medium'),
                func.sum(
                    case(
                        (and_(AnalysisResult.overall_risk_score >= 60, AnalysisResult.overall_risk_score < 90), 1),
                        else_=0
                    )
                ).label('high'),
                func.sum(
                    case((AnalysisResult.overall_risk_score >= 90, 1), else_=0)
                ).label('critical')
            )
            .select_from(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == user_id)
        )
        
        result = await db.execute(risk_query)
        row = result.first()
        
        if row:
            return RiskDistribution(
                low=row.low or 0,
                medium=row.medium or 0,
                high=row.high or 0,
                critical=row.critical or 0,
                total=row.total or 0
            )
        else:
            return RiskDistribution(low=0, medium=0, high=0, critical=0, total=0)
        
    except Exception as e:
        logger.error(f"Failed to calculate risk distribution: {str(e)}")
        return RiskDistribution(low=0, medium=0, high=0, critical=0, total=0)


async def _get_most_common_violations(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """Get most common rule violations."""
    try:
        # This would need to be implemented based on the actual rule_violations structure
        # For now, return empty list
        return []
        
    except Exception as e:
        logger.error(f"Failed to get common violations: {str(e)}")
        return []


async def _get_trend_data_optimized(db: AsyncSession, user_id: str, days: int = 30) -> List[TrendDataPoint]:
    """Get trend data using single optimized query with conditional aggregation."""
    try:
        query_start_time = datetime.utcnow()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Single optimized query with conditional aggregation for risk distribution
        trend_query = (
            select(
                func.date(AnalysisResult.analysis_timestamp).label('date'),
                func.count(AnalysisResult.id).label('count'),
                func.avg(AnalysisResult.overall_risk_score).label('avg_risk'),
                # Risk distribution calculated in same query using conditional aggregation
                func.sum(case((AnalysisResult.overall_risk_score < 30, 1), else_=0)).label('risk_low'),
                func.sum(case((and_(AnalysisResult.overall_risk_score >= 30, AnalysisResult.overall_risk_score < 60), 1), else_=0)).label('risk_medium'),
                func.sum(case((and_(AnalysisResult.overall_risk_score >= 60, AnalysisResult.overall_risk_score < 80), 1), else_=0)).label('risk_high'),
                func.sum(case((AnalysisResult.overall_risk_score >= 80, 1), else_=0)).label('risk_critical')
            )
            .select_from(AnalysisResult)
            .join(FileRecord)  # Join for user filtering
            .where(
                and_(
                    FileRecord.user_id == user_id,
                    AnalysisResult.analysis_timestamp >= start_date
                )
            )
            .group_by(func.date(AnalysisResult.analysis_timestamp))
            .order_by(func.date(AnalysisResult.analysis_timestamp))
        )
        
        # Log single query execution for performance verification
        logger.info(f"Executing optimized trend data query for user {user_id} ({days} days) - SINGLE QUERY")
        
        result = await db.execute(trend_query)
        
        query_end_time = datetime.utcnow()
        query_duration = (query_end_time - query_start_time).total_seconds()
        
        trend_data = []
        
        # Build TrendDataPoint objects from single query results
        for row in result.fetchall():
            date, count, avg_risk, risk_low, risk_medium, risk_high, risk_critical = row
            
            # Build RiskDistribution from single query results
            risk_dist = RiskDistribution(
                low=risk_low or 0,
                medium=risk_medium or 0,
                high=risk_high or 0,
                critical=risk_critical or 0,
                total=count or 0
            )
            
            trend_data.append(TrendDataPoint(
                date=datetime.combine(date, datetime.min.time()),
                count=count,
                average_risk_score=float(avg_risk) if avg_risk else 0.0,
                risk_distribution=risk_dist
            ))
        
        # Log performance metrics
        logger.info(f"Optimized trend data query completed in {query_duration:.4f}s, returned {len(trend_data)} data points")
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Failed to get optimized trend data: {str(e)}")
        return []




async def _get_processing_stats(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Get processing performance statistics."""
    try:
        # Get basic processing stats
        stats_query = (
            select(
                func.count(AnalysisResult.id),
                func.avg(AnalysisResult.forensics_score),
                func.avg(AnalysisResult.ocr_confidence)
            )
            .where(AnalysisResult.file.has(FileRecord.user_id == user_id))
        )
        
        result = await db.execute(stats_query)
        stats_result = result.first()
        count, avg_forensics, avg_ocr = stats_result if stats_result else (None, None, None)
        
        return {
            'total_processed': count or 0,
            'average_forensics_score': float(avg_forensics) if avg_forensics else 0.0,
            'average_ocr_confidence': float(avg_ocr) if avg_ocr else 0.0,
            'processing_time': 0.0,  # TODO: Implement actual processing time tracking
            'success_rate': 100.0    # TODO: Implement error tracking
        }
        
    except Exception as e:
        logger.error(f"Failed to get processing stats: {str(e)}")
        return {
            'total_processed': 0,
            'average_forensics_score': 0.0,
            'average_ocr_confidence': 0.0,
            'processing_time': 0.0,
            'success_rate': 0.0
        }


async def _apply_filters(query, filters: DashboardFilter):
    """Apply filters to the query."""
    if not filters:
        return query
    
    # Time range filter
    if filters.time_range:
        end_date = datetime.utcnow()
        
        if filters.time_range == TimeRange.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif filters.time_range == TimeRange.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        elif filters.time_range == TimeRange.LAST_90_DAYS:
            start_date = end_date - timedelta(days=90)
        elif filters.time_range == TimeRange.LAST_YEAR:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None
        
        if start_date:
            query = query.where(AnalysisResult.analysis_timestamp >= start_date)
    
    # Custom date range filter
    if filters.custom_date_range:
        query = query.where(
            and_(
                AnalysisResult.analysis_timestamp >= filters.custom_date_range.start,
                AnalysisResult.analysis_timestamp <= filters.custom_date_range.end
            )
        )
    
    # Risk score range filter
    if filters.risk_score_range:
        query = query.where(
            and_(
                AnalysisResult.overall_risk_score >= filters.risk_score_range.min,
                AnalysisResult.overall_risk_score <= filters.risk_score_range.max
            )
        )
    
    # File type filter
    if filters.file_types:
        query = query.where(FileRecord.mime_type.in_(filters.file_types))
    
    # Confidence filter
    if filters.min_confidence:
        query = query.where(AnalysisResult.ocr_confidence >= filters.min_confidence)
    
    return query


async def _apply_sorting(query, pagination: PaginationParams):
    """Apply sorting to the query."""
    sort_column: Any = AnalysisResult.analysis_timestamp  # Default
    
    if pagination.sort_field == SortField.UPLOAD_TIMESTAMP:
        sort_column = FileRecord.upload_timestamp
    elif pagination.sort_field == SortField.FILENAME:
        sort_column = FileRecord.filename
    elif pagination.sort_field == SortField.FILE_SIZE:
        sort_column = FileRecord.file_size
    elif pagination.sort_field == SortField.RISK_SCORE:
        sort_column = AnalysisResult.overall_risk_score
    
    if pagination.sort_direction == SortDirection.ASC:
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    return query


async def _convert_to_enhanced_result(analysis: AnalysisResult) -> EnhancedAnalysisResult:
    """Convert AnalysisResult to EnhancedAnalysisResult."""
    try:
        # Calculate risk score details
        risk_score_details = RiskScoreDetails(
            overall_score=int(analysis.overall_risk_score),
            risk_level=_get_risk_level_from_score(analysis.overall_risk_score),
            category_scores=CategoryScore(
                forensics=analysis.forensics_score,
                ocr=analysis.ocr_confidence,
                rules=analysis.overall_risk_score
            ),
            risk_factors=analysis.rule_violations.get('violations', []) if analysis.rule_violations else [],
            confidence_level=analysis.ocr_confidence,
            recommendations=analysis.rule_violations.get('recommendations', []) if analysis.rule_violations else []
        )
        
        return EnhancedAnalysisResult(
            id=analysis.id,
            file_id=analysis.file_id,
            filename=analysis.file.filename,
            file_size=analysis.file.file_size,
            mime_type=analysis.file.mime_type,
            upload_timestamp=analysis.file.upload_timestamp,
            analysis_timestamp=analysis.analysis_timestamp,
            risk_score_details=risk_score_details,
            forensics_score=analysis.forensics_score,
            ocr_confidence=analysis.ocr_confidence,
            overall_risk_score=analysis.overall_risk_score,
            violations=analysis.rule_violations.get('violations', []) if analysis.rule_violations else [],
            processing_time=None  # TODO: Implement processing time tracking
        )
        
    except Exception as e:
        logger.error(f"Failed to convert to enhanced result: {str(e)}")
        raise


def _get_risk_level_from_score(score: float) -> RiskLevel:
    """Determine risk level from score using the same thresholds as scoring engine."""
    # Load thresholds from scoring config to ensure consistency
    config_path = Path(__file__).parent.parent.parent / "config" / "scoring_config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        thresholds = config['risk_thresholds']
        
        if score >= thresholds['CRITICAL']:
            return RiskLevel.CRITICAL
        elif score >= thresholds['HIGH']:
            return RiskLevel.HIGH
        elif score >= thresholds['MEDIUM']:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
            
    except Exception as e:
        # Fallback to hardcoded values if config can't be loaded
        logging.warning(f"Could not load scoring config: {e}")
        if score >= 90:
            return RiskLevel.CRITICAL
        elif score >= 80:
            return RiskLevel.HIGH
        elif score >= 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


async def _get_filtered_summary(db: AsyncSession, user_id: str, filters: DashboardFilter) -> Dict[str, Any]:
    """Get summary statistics for filtered results."""
    try:
        # Build base query with filters
        base_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == user_id)
        )
        
        filtered_query = await _apply_filters(base_query, filters)
        
        # Get summary stats
        summary_query = (
            select(
                func.count(AnalysisResult.id),
                func.avg(AnalysisResult.overall_risk_score),
                func.avg(AnalysisResult.ocr_confidence)
            )
            .select_from(filtered_query.subquery())
        )
        
        result = await db.execute(summary_query)
        summary_result = result.first()
        count, avg_risk, avg_confidence = summary_result if summary_result else (None, None, None)
        
        return {
            'total_filtered': count or 0,
            'average_risk_score': float(avg_risk) if avg_risk else 0.0,
            'average_confidence': float(avg_confidence) if avg_confidence else 0.0
        }
        
    except Exception as e:
        logger.error(f"Failed to get filtered summary: {str(e)}")
        return {
            'total_filtered': 0,
            'average_risk_score': 0.0,
            'average_confidence': 0.0
        }


async def _get_system_health(db: AsyncSession) -> Dict[str, Any]:
    """Get system health information."""
    try:
        return {
            'database_status': 'healthy',
            'api_response_time': 0.0,  # TODO: Implement actual response time tracking
            'storage_usage': 0.0,      # TODO: Implement storage usage tracking
            'last_health_check': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        return {
            'database_status': 'error',
            'api_response_time': 0.0,
            'storage_usage': 0.0,
            'last_health_check': datetime.utcnow()
        }
