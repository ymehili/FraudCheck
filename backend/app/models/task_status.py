from sqlalchemy import String, Float, DateTime, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import TYPE_CHECKING, Optional
import enum

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .file import FileRecord
    from .analysis import AnalysisResult


class TaskStatusEnum(enum.Enum):
    """Enum for task status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


class TaskStatus(Base):
    """Model for tracking background task status and progress."""
    __tablename__ = "task_status"

    # Primary key
    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Status and progress
    status: Mapped[TaskStatusEnum] = mapped_column(
        SQLEnum(TaskStatusEnum), 
        nullable=False, 
        default=TaskStatusEnum.PENDING
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Foreign keys
    file_id: Mapped[str] = mapped_column(
        String, ForeignKey("files.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    
    # Optional result reference
    result_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("analysis_results.id"), nullable=True
    )
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Estimated completion time (in seconds)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="task_statuses")
    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="task_statuses")
    result: Mapped[Optional["AnalysisResult"]] = relationship("AnalysisResult", uselist=False)
    
    def __repr__(self) -> str:
        return f"<TaskStatus(task_id={self.task_id}, status={self.status.value}, progress={self.progress})>"