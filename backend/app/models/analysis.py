from sqlalchemy import String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import TYPE_CHECKING

from ..database import Base

if TYPE_CHECKING:
    from .file import FileRecord
    from .search_index import SearchIndex


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_id: Mapped[str] = mapped_column(
        String, ForeignKey("files.id"), nullable=False
    )
    analysis_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Forensics results
    forensics_score: Mapped[float] = mapped_column(Float, nullable=False)
    edge_inconsistencies: Mapped[dict] = mapped_column(JSON, nullable=False)
    compression_artifacts: Mapped[dict] = mapped_column(JSON, nullable=False)
    font_analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # OCR results
    ocr_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Rule engine results
    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    rule_violations: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_factors: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Relationships
    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="analysis_results")
    search_index: Mapped["SearchIndex"] = relationship("SearchIndex", back_populates="analysis", uselist=False)