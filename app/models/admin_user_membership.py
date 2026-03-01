from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AdminUserMembership(Base):
    __tablename__ = "admin_user_memberships"

    __table_args__ = (
        UniqueConstraint(
            "admin_user_id",
            "organization_id",
            name="uq_admin_user_memberships_user_org",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String(50), nullable=False, default="viewer", server_default="viewer")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    admin_user = relationship("AdminUser", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")