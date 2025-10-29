"""
models.py - Data Models and Enums
"""

from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """Error codes for API responses"""
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_COURIER = "INVALID_COURIER"
    INVALID_REGION = "INVALID_REGION"
    CONFIG_ERROR = "CONFIG_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class DeliveryEstimate:
    """Delivery estimation result"""
    courier: str
    region: str
    order_time: str
    cutoff_time: str
    before_cutoff: bool
    processing_note: str
    start_date: str
    base_delivery_days: int
    estimated_delivery_date: str
    total_calendar_days: int
    confidence_level: str = "high"  # high, medium, low
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "courier": self.courier,
            "region": self.region,
            "order_time": self.order_time,
            "cutoff_time": self.cutoff_time,
            "before_cutoff": self.before_cutoff,
            "processing_note": self.processing_note,
            "start_date": self.start_date,
            "base_delivery_days": self.base_delivery_days,
            "estimated_delivery_date": self.estimated_delivery_date,
            "total_calendar_days": self.total_calendar_days,
            "confidence_level": self.confidence_level
        }