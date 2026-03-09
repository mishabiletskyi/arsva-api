from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vapi_call_id = Column(String(255), nullable=True, index=True)
    call_outcome = Column(String(100), nullable=True, index=True)
    script_version = Column(String(100), nullable=True)

    transcript = Column(Text, nullable=True)
    recording_url = Column(Text, nullable=True)

    opt_out_detected = Column(Boolean, nullable=False, default=False, server_default="false")
    expected_payment_date = Column(Date, nullable=True)

    duration_seconds = Column(Integer, nullable=True)
    raw_payload = Column(Text, nullable=True)
    sms_sent = Column(Boolean, nullable=False, default=False, server_default="false")
    sms_status = Column(String(100), nullable=True)
    sms_message_sid = Column(String(255), nullable=True, index=True)
    sms_error_message = Column(Text, nullable=True)
    sms_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    organization = relationship("Organization", back_populates="call_logs")
    property = relationship("Property", back_populates="call_logs")
    tenant = relationship("Tenant", back_populates="call_logs")
