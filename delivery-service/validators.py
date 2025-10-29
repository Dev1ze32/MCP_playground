"""
validators.py - Input Validation and Sanitization
"""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes user inputs"""
    
    # Allowed values (can be moved to config if needed)
    ALLOWED_COURIERS = ["J&T", "LBC", "JRS", "NINJAVAN", "LALAMOVE", "GRAB", "ENTREGO"]
    ALLOWED_REGIONS = ["ncr", "luzon", "visayas", "mindanao"]
    
    # Maximum lengths to prevent abuse
    MAX_COURIER_LENGTH = 50
    MAX_REGION_LENGTH = 50
    
    @staticmethod
    def validate_courier(courier_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and normalize courier name
        
        Args:
            courier_name: Raw courier name input
            
        Returns:
            Tuple of (is_valid, normalized_value, error_message)
        """
        # Check if provided
        if not courier_name:
            return False, None, "Courier name is required"
        
        # Check type
        if not isinstance(courier_name, str):
            return False, None, "Courier name must be a string"
        
        # Normalize: strip whitespace and convert to uppercase
        normalized = courier_name.strip().upper()
        
        # Check if empty after stripping
        if not normalized:
            return False, None, "Courier name cannot be empty"
        
        # Check length
        if len(normalized) > InputValidator.MAX_COURIER_LENGTH:
            return False, None, f"Courier name too long (max {InputValidator.MAX_COURIER_LENGTH} characters)"
        
        # Check for invalid characters (basic sanitization)
        if not normalized.replace('&', '').replace('-', '').replace(' ', '').isalnum():
            return False, None, "Courier name contains invalid characters"
        
        # Note: We don't check against ALLOWED_COURIERS here to allow flexibility
        # The config will determine if the courier is actually supported
        
        logger.debug(f"Courier validated: '{courier_name}' -> '{normalized}'")
        return True, normalized, None
    
    @staticmethod
    def validate_region(region: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and normalize region
        
        Args:
            region: Raw region input
            
        Returns:
            Tuple of (is_valid, normalized_value, error_message)
        """
        # Check if provided
        if not region:
            return False, None, "Region is required"
        
        # Check type
        if not isinstance(region, str):
            return False, None, "Region must be a string"
        
        # Normalize: strip whitespace and convert to lowercase
        normalized = region.strip().lower()
        
        # Check if empty after stripping
        if not normalized:
            return False, None, "Region cannot be empty"
        
        # Check length
        if len(normalized) > InputValidator.MAX_REGION_LENGTH:
            return False, None, f"Region name too long (max {InputValidator.MAX_REGION_LENGTH} characters)"
        
        # Check against allowed regions
        if normalized not in InputValidator.ALLOWED_REGIONS:
            return False, None, (
                f"Invalid region '{normalized}'. "
                f"Allowed regions: {', '.join(InputValidator.ALLOWED_REGIONS)}"
            )
        
        logger.debug(f"Region validated: '{region}' -> '{normalized}'")
        return True, normalized, None
    
    @staticmethod
    def validate_date_string(date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate date string format (YYYY-MM-DD)
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, normalized_value, error_message)
        """
        from datetime import datetime
        
        if not date_str:
            return False, None, "Date is required"
        
        if not isinstance(date_str, str):
            return False, None, "Date must be a string"
        
        # Try to parse the date
        try:
            parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d')
            normalized = parsed_date.strftime('%Y-%m-%d')
            return True, normalized, None
        except ValueError:
            return False, None, "Invalid date format. Expected: YYYY-MM-DD"
    
    @staticmethod
    def add_allowed_courier(courier_name: str):
        """
        Add a courier to the allowed list (for dynamic configuration)
        
        Args:
            courier_name: Courier name to add
        """
        normalized = courier_name.strip().upper()
        if normalized and normalized not in InputValidator.ALLOWED_COURIERS:
            InputValidator.ALLOWED_COURIERS.append(normalized)
            logger.info(f"Added courier to allowed list: {normalized}")
    
    @staticmethod
    def add_allowed_region(region_name: str):
        """
        Add a region to the allowed list (for dynamic configuration)
        
        Args:
            region_name: Region name to add
        """
        normalized = region_name.strip().lower()
        if normalized and normalized not in InputValidator.ALLOWED_REGIONS:
            InputValidator.ALLOWED_REGIONS.append(normalized)
            logger.info(f"Added region to allowed list: {normalized}")