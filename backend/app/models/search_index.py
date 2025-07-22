"""
Search Index model for optimized full-text search.
"""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class SearchIndex(Base):
    """Optimized search index for dashboard search functionality."""
    
    __tablename__ = "search_index"
    
    id = Column(String, primary_key=True)
    analysis_id = Column(String, ForeignKey("analysis_results.id"), nullable=False, unique=True)
    filename = Column(String, nullable=False, server_default="")
    violations_text = Column(Text, nullable=False, server_default="")
    risk_factors_text = Column(Text, nullable=False, server_default="")
    ocr_text = Column(Text, nullable=False, server_default="")
    search_text = Column(Text, nullable=False, server_default="")
    
    # Relationships
    analysis = relationship("AnalysisResult", back_populates="search_index")