from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import TYPE_CHECKING, List

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .analysis import AnalysisResult


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    s3_url: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="files")
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult", back_populates="file"
    )
    
    def __init__(self, **kwargs):
        # Handle content_type alias for mime_type
        if 'content_type' in kwargs:
            kwargs['mime_type'] = kwargs.pop('content_type')
        super().__init__(**kwargs)