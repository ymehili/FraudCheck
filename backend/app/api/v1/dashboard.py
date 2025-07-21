"""
Dashboard API endpoints for CheckGuard AI.

This module provides comprehensive dashboard functionality including:
- Dashboard statistics and overview
- Analysis history with filtering and pagination
- Risk distribution analytics
- Trend analysis
- Export functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from ...database import get_db
from ...models.user import User
from ...models.file import FileRecord
from ...models.analysis import AnalysisResult
from ...schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    AnalysisHistoryResponse,
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

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)


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
    try:
        # Get total analyses count
        total_analyses = await db.scalar(
            select(func.count(AnalysisResult.id))
            .where(AnalysisResult.file.has(FileRecord.user_id == current_user.id))
        )
        
        # Get today's analyses
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        analyses_today = await db.scalar(
            select(func.count(AnalysisResult.id))
            .where(
                and_(
                    AnalysisResult.file.has(FileRecord.user_id == current_user.id),
                    AnalysisResult.analysis_timestamp >= today_start
                )
            )
        )
        
        # Get this week's analyses
        week_start = today_start - timedelta(days=today_start.weekday())
        analyses_this_week = await db.scalar(
            select(func.count(AnalysisResult.id))
            .where(
                and_(
                    AnalysisResult.file.has(FileRecord.user_id == current_user.id),
                    AnalysisResult.analysis_timestamp >= week_start
                )
            )
        )
        
        # Get this month's analyses
        month_start = today_start.replace(day=1)
        analyses_this_month = await db.scalar(
            select(func.count(AnalysisResult.id))
            .where(
                and_(
                    AnalysisResult.file.has(FileRecord.user_id == current_user.id),
                    AnalysisResult.analysis_timestamp >= month_start
                )
            )
        )
        
        # Get risk distribution
        risk_distribution = await _get_risk_distribution(db, current_user.id)
        
        # Get average risk score and confidence
        avg_stats = await db.execute(
            select(
                func.avg(AnalysisResult.overall_risk_score),
                func.avg(AnalysisResult.ocr_confidence)
            )
            .where(AnalysisResult.file.has(FileRecord.user_id == current_user.id))
        )
        result = avg_stats.first()
        avg_risk_score, avg_confidence = result if result else (None, None)
        
        # Get most common violations
        most_common_violations = await _get_most_common_violations(db, current_user.id)
        
        # Get trend data for the last 30 days
        trend_data = await _get_trend_data(db, current_user.id, days=30)
        
        # Get processing statistics
        processing_stats = await _get_processing_stats(db, current_user.id)
        
        return DashboardStats(
            total_analyses=total_analyses or 0,
            analyses_today=analyses_today or 0,
            analyses_this_week=analyses_this_week or 0,
            analyses_this_month=analyses_this_month or 0,
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
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )


@router.get("/history", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    filters: DashboardFilter = Depends(),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated analysis history with filtering.
    
    Supports filtering by:
    - Date range
    - Risk score range
    - Risk levels
    - File types
    - Presence of violations
    """
    try:
        # Build base query
        base_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == current_user.id)
            .options(joinedload(AnalysisResult.file))
        )
        
        # Apply filters
        filtered_query = await _apply_filters(base_query, filters)
        
        # Apply sorting
        sorted_query = await _apply_sorting(filtered_query, pagination)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(filtered_query.subquery())
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.per_page
        paginated_query = sorted_query.offset(offset).limit(pagination.per_page)
        
        # Execute query
        result = await db.execute(paginated_query)
        analyses = result.scalars().all()
        
        # Convert to enhanced analysis results
        enhanced_analyses = []
        for analysis in analyses:
            enhanced_analysis = await _convert_to_enhanced_result(analysis)
            enhanced_analyses.append(enhanced_analysis)
        
        # Calculate pagination info
        total_pages = ((total_count or 0) + pagination.per_page - 1) // pagination.per_page
        
        pagination_info = {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_items': total_count,
            'total_pages': total_pages,
            'has_next': pagination.page < total_pages,
            'has_previous': pagination.page > 1
        }
        
        # Get summary statistics for filtered results
        summary = await _get_filtered_summary(db, current_user.id, filters)
        
        return AnalysisHistoryResponse(
            analyses=enhanced_analyses,
            pagination=pagination_info,
            filters_applied=filters,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Failed to get analysis history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis history: {str(e)}"
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
            detail=f"Failed to retrieve filter options: {str(e)}"
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
        
        # Build search query
        search_query = (
            select(AnalysisResult)
            .join(FileRecord)
            .where(FileRecord.user_id == current_user.id)
            .options(joinedload(AnalysisResult.file))
        )
        
        # Apply text search
        search_conditions = []
        query_term = f"%{search_request.query}%"
        
        if 'filename' in search_request.search_fields:
            search_conditions.append(FileRecord.filename.ilike(query_term))
        
        if 'violations' in search_request.search_fields:
            search_conditions.append(
                func.json_extract(AnalysisResult.rule_violations, '$.violations').ilike(query_term)
            )
        
        if 'risk_factors' in search_request.search_fields:
            search_conditions.append(
                func.json_extract(AnalysisResult.rule_violations, '$.risk_factors').ilike(query_term)
            )
        
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
            detail=f"Search failed: {str(e)}"
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
            detail=f"Failed to retrieve dashboard: {str(e)}"
        )


# Helper functions
async def _get_risk_distribution(db: AsyncSession, user_id: str) -> RiskDistribution:
    """Calculate risk distribution for user's analyses."""
    try:
        # Get all analyses for the user
        analyses_query = (
            select(AnalysisResult.overall_risk_score)
            .where(AnalysisResult.file.has(FileRecord.user_id == user_id))
        )
        
        result = await db.execute(analyses_query)
        risk_scores = [row[0] for row in result.fetchall()]
        
        # Categorize by risk levels
        low = sum(1 for score in risk_scores if score < 30)
        medium = sum(1 for score in risk_scores if 30 <= score < 60)
        high = sum(1 for score in risk_scores if 60 <= score < 80)
        critical = sum(1 for score in risk_scores if score >= 80)
        
        return RiskDistribution(
            low=low,
            medium=medium,
            high=high,
            critical=critical,
            total=len(risk_scores)
        )
        
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


async def _get_trend_data(db: AsyncSession, user_id: str, days: int = 30) -> List[TrendDataPoint]:
    """Get trend data for the specified number of days."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get analyses grouped by date
        trend_query = (
            select(
                func.date(AnalysisResult.analysis_timestamp).label('date'),
                func.count(AnalysisResult.id).label('count'),
                func.avg(AnalysisResult.overall_risk_score).label('avg_risk')
            )
            .where(
                and_(
                    AnalysisResult.file.has(FileRecord.user_id == user_id),
                    AnalysisResult.analysis_timestamp >= start_date
                )
            )
            .group_by(func.date(AnalysisResult.analysis_timestamp))
            .order_by(func.date(AnalysisResult.analysis_timestamp))
        )
        
        result = await db.execute(trend_query)
        trend_data = []
        
        for row in result.fetchall():
            date, count, avg_risk = row
            
            # Calculate risk distribution for this date
            risk_dist = await _get_risk_distribution_for_date(db, user_id, date)
            
            trend_data.append(TrendDataPoint(
                date=datetime.combine(date, datetime.min.time()),
                count=count,
                average_risk_score=float(avg_risk) if avg_risk else 0.0,
                risk_distribution=risk_dist
            ))
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Failed to get trend data: {str(e)}")
        return []


async def _get_risk_distribution_for_date(db: AsyncSession, user_id: str, date) -> RiskDistribution:
    """Get risk distribution for a specific date."""
    try:
        analyses_query = (
            select(AnalysisResult.overall_risk_score)
            .where(
                and_(
                    AnalysisResult.file.has(FileRecord.user_id == user_id),
                    func.date(AnalysisResult.analysis_timestamp) == date
                )
            )
        )
        
        result = await db.execute(analyses_query)
        risk_scores = [row[0] for row in result.fetchall()]
        
        low = sum(1 for score in risk_scores if score < 30)
        medium = sum(1 for score in risk_scores if 30 <= score < 60)
        high = sum(1 for score in risk_scores if 60 <= score < 80)
        critical = sum(1 for score in risk_scores if score >= 80)
        
        return RiskDistribution(
            low=low,
            medium=medium,
            high=high,
            critical=critical,
            total=len(risk_scores)
        )
        
    except Exception as e:
        logger.error(f"Failed to get risk distribution for date: {str(e)}")
        return RiskDistribution(low=0, medium=0, high=0, critical=0, total=0)


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
    """Determine risk level from score."""
    if score >= 80:
        return RiskLevel.CRITICAL
    elif score >= 60:
        return RiskLevel.HIGH
    elif score >= 30:
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
