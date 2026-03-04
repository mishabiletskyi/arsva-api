from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class DashboardTask(Base):
    __tablename__ = "dashboard_tasks"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'done')",
            name="ck_dashboard_tasks_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending", server_default="pending")
    created_by_admin_id = Column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization = relationship("Organization")
    property = relationship("Property")
    created_by = relationship("AdminUser")
