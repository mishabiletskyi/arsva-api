from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class CallPolicy(Base):
    __tablename__ = "call_policies"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "property_id",
            name="uq_call_policies_org_property",
        ),
        CheckConstraint(
            "min_hours_between_calls >= 1 AND min_hours_between_calls <= 720",
            name="ck_call_policies_min_hours_between_calls",
        ),
        CheckConstraint(
            "max_calls_7d >= 0 AND max_calls_7d <= 14",
            name="ck_call_policies_max_calls_7d",
        ),
        CheckConstraint(
            "max_calls_30d >= 0 AND max_calls_30d <= 60",
            name="ck_call_policies_max_calls_30d",
        ),
        CheckConstraint(
            "days_late_min >= 0",
            name="ck_call_policies_days_late_min",
        ),
        CheckConstraint(
            "days_late_max >= days_late_min",
            name="ck_call_policies_days_late_max",
        ),
        CheckConstraint(
            "length(call_window_start) = 5 "
            "AND substr(call_window_start, 3, 1) = ':' "
            "AND CAST(substr(call_window_start, 1, 2) AS INTEGER) BETWEEN 0 AND 23 "
            "AND CAST(substr(call_window_start, 4, 2) AS INTEGER) BETWEEN 0 AND 59",
            name="ck_call_policies_call_window_start_format",
        ),
        CheckConstraint(
            "length(call_window_end) = 5 "
            "AND substr(call_window_end, 3, 1) = ':' "
            "AND CAST(substr(call_window_end, 1, 2) AS INTEGER) BETWEEN 0 AND 23 "
            "AND CAST(substr(call_window_end, 4, 2) AS INTEGER) BETWEEN 0 AND 59",
            name="ck_call_policies_call_window_end_format",
        ),
        CheckConstraint(
            "call_window_start <> call_window_end",
            name="ck_call_policies_call_window_not_equal",
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

    min_hours_between_calls = Column(
        Integer,
        nullable=False,
        default=72,
        server_default="72",
    )
    max_calls_7d = Column(Integer, nullable=False, default=2, server_default="2")
    max_calls_30d = Column(Integer, nullable=False, default=4, server_default="4")
    call_window_start = Column(String(5), nullable=False, default="08:00", server_default="08:00")
    call_window_end = Column(String(5), nullable=False, default="21:00", server_default="21:00")
    days_late_min = Column(Integer, nullable=False, default=3, server_default="3")
    days_late_max = Column(Integer, nullable=False, default=10, server_default="10")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization = relationship("Organization", back_populates="call_policies")
    property = relationship("Property", back_populates="call_policies")
