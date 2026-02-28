from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CsvImport(Base):
    __tablename__ = "csv_imports"

    id = Column(Integer, primary_key=True, index=True)

    original_file_name = Column(String(255), nullable=False)
    stored_file_name = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False, default="pending", server_default="pending")

    total_rows = Column(Integer, nullable=False, default=0, server_default="0")
    imported_rows = Column(Integer, nullable=False, default=0, server_default="0")
    failed_rows = Column(Integer, nullable=False, default=0, server_default="0")

    error_message = Column(Text, nullable=True)

    uploaded_by_admin_id = Column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    uploaded_by = relationship("AdminUser", back_populates="csv_imports")