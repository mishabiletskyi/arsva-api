from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PropertyUserAccess(Base):
    __tablename__ = "property_user_access"

    __table_args__ = (
        UniqueConstraint(
            "admin_user_id",
            "property_id",
            name="uq_property_user_access_user_property",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    admin_user = relationship("AdminUser", back_populates="property_accesses")
    property = relationship("Property", back_populates="user_access")