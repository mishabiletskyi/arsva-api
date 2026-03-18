import builtins

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class OutboundCallJob(Base):
    __tablename__ = "outbound_call_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'previewed', 'processing', 'completed', 'failed')",
            name="ck_outbound_call_jobs_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(50), nullable=False, default="previewed", server_default="previewed")
    trigger_mode = Column(String(50), nullable=False, default="manual", server_default="manual")
    dry_run = Column(Boolean, nullable=False, default=True, server_default="true")
    requested_by_admin_id = Column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    total_candidates = Column(Integer, nullable=False, default=0, server_default="0")
    eligible_count = Column(Integer, nullable=False, default=0, server_default="0")
    blocked_count = Column(Integer, nullable=False, default=0, server_default="0")
    filters = Column(JSON, nullable=True)
    policy_snapshot = Column(JSON, nullable=True)
    result_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization = relationship("Organization")
    property = relationship("Property")
    requested_by = relationship("AdminUser")

    @builtins.property
    def requested_count(self) -> int:
        return self.total_candidates

    @builtins.property
    def started_count(self) -> int:
        if not self.result_summary:
            return 0
        value = self.result_summary.get("started_count")
        return int(value) if isinstance(value, int) else 0

    @builtins.property
    def failed_count(self) -> int:
        if not self.result_summary:
            return 0
        value = self.result_summary.get("failed_count")
        return int(value) if isinstance(value, int) else 0

    @builtins.property
    def note(self) -> str | None:
        if not self.result_summary:
            return None
        value = self.result_summary.get("note")
        return value if isinstance(value, str) else None
