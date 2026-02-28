from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    vapi_call_id = Column(String(255), nullable=True, index=True)
    call_outcome = Column(String(100), nullable=True, index=True)

    transcript = Column(Text, nullable=True)
    recording_url = Column(Text, nullable=True)

    opt_out_detected = Column(Boolean, nullable=False, default=False, server_default="false")
    expected_payment_date = Column(Date, nullable=True)

    duration_seconds = Column(Integer, nullable=True)
    raw_payload = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    tenant = relationship("Tenant", back_populates="call_logs")