import logging
import time
import pytz
import threading
from typing import Dict, Optional
from sheetCredential import get_sheet_data, parse_to_config

logger = logging.getLogger(__name__)


class ConfigCache:
    """
    Thread-safe configuration cache with TTL
    
    NOTE: This is a SHARED cache - all users see the same configuration.
    This is appropriate for most e-commerce scenarios where delivery rates
    are the same for all customers.
    """
    
    _cache: Optional[Dict] = None
    _cache_time: Optional[float] = None
    _cache_ttl: int = 600  # 10 minutes in seconds
    _lock = threading.Lock()  # Thread safety for concurrent requests
    _fetch_in_progress = False  # Prevent multiple simultaneous fetches
    
    @classmethod
    def get_config(cls, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get cached configuration or fetch new one if expired
        Thread-safe for multiple concurrent users
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh config
            
        Returns:
            Configuration dictionary or None if unavailable
        """
        with cls._lock:
            current_time = time.time()
            
            # Check if cache is valid
            if (not force_refresh and 
                cls._cache is not None and 
                cls._cache_time is not None and
                (current_time - cls._cache_time) < cls._cache_ttl):
                logger.debug("Using cached configuration (shared)")
                return cls._cache
            
            # If another thread is already fetching, wait and return stale cache
            if cls._fetch_in_progress:
                logger.info("Config fetch already in progress, returning stale cache")
                return cls._cache
            
            # Mark fetch in progress
            cls._fetch_in_progress = True
        
        # Fetch outside the lock to avoid blocking other threads
        try:
            logger.info("Fetching fresh configuration from Google Sheets")
            sheet_data = get_sheet_data()
            
            if not sheet_data:
                logger.error("Empty data received from Google Sheets")
                with cls._lock:
                    cls._fetch_in_progress = False
                # Return stale cache if available
                if cls._cache is not None:
                    logger.warning("Using stale cache due to fetch failure")
                    return cls._cache
                raise ValueError("No configuration data available")
            
            config = parse_to_config(sheet_data)
            
            # Validate configuration structure
            if not cls._validate_config(config):
                logger.error("Configuration validation failed")
                with cls._lock:
                    cls._fetch_in_progress = False
                # Return stale cache if available
                if cls._cache is not None:
                    logger.warning("Using stale cache due to validation failure")
                    return cls._cache
                raise ValueError("Invalid configuration structure")
            
            # Update cache (thread-safe)
            with cls._lock:
                cls._cache = config
                cls._cache_time = current_time
                cls._fetch_in_progress = False
                logger.info("Configuration cache updated successfully (shared)")
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
            with cls._lock:
                cls._fetch_in_progress = False
            # Return stale cache if available
            if cls._cache is not None:
                logger.warning("Using stale cache due to error")
                return cls._cache
            raise
    
    @classmethod
    def _validate_config(cls, config: Dict) -> bool:
        """
        Validate configuration structure
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ["couriers", "cutoff_time", "timezone"]
        
        # Check required keys exist
        if not all(key in config for key in required_keys):
            logger.error(f"Missing required config keys. Required: {required_keys}")
            return False
        
        # Validate couriers is a dictionary
        if not isinstance(config["couriers"], dict):
            logger.error("Couriers config must be a dictionary")
            return False
        
        # Validate at least one courier exists
        if len(config["couriers"]) == 0:
            logger.error("No couriers configured")
            return False
        
        # Validate cutoff time format (HH:MM)
        try:
            cutoff_time = config["cutoff_time"]
            if not isinstance(cutoff_time, str) or ':' not in cutoff_time:
                raise ValueError("Invalid format")
            
            hours, minutes = map(int, cutoff_time.split(':'))
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError("Invalid time values")
                
        except Exception as e:
            logger.error(f"Invalid cutoff_time format: {config.get('cutoff_time')} - {str(e)}")
            return False
        
        # Validate timezone
        try:
            pytz.timezone(config["timezone"])
        except Exception as e:
            logger.error(f"Invalid timezone: {config.get('timezone')} - {str(e)}")
            return False
        
        # Validate each courier has valid region data
        for courier_name, regions in config["couriers"].items():
            if not isinstance(regions, dict):
                logger.error(f"Courier '{courier_name}' regions must be a dictionary")
                return False
            
            for region_name, days in regions.items():
                if not isinstance(days, int) or days <= 0:
                    logger.error(f"Invalid delivery days for {courier_name}/{region_name}: {days}")
                    return False
        
        logger.debug("Configuration validation passed")
        return True
    
    @classmethod
    def clear_cache(cls):
        """Clear the configuration cache (useful for testing)"""
        with cls._lock:
            cls._cache = None
            cls._cache_time = None
            logger.info("Configuration cache cleared")
    
    @classmethod
    def set_cache_ttl(cls, ttl_seconds: int):
        """
        Set the cache TTL
        
        Args:
            ttl_seconds: Time to live in seconds
        """
        if ttl_seconds < 0:
            logger.warning(f"Invalid TTL value: {ttl_seconds}, using default")
            return
        
        with cls._lock:
            cls._cache_ttl = ttl_seconds
            logger.info(f"Cache TTL set to {ttl_seconds} seconds")
    
    @classmethod
    def get_cache_info(cls) -> Dict:
        """
        Get information about the current cache state
        
        Returns:
            Dictionary with cache information
        """
        with cls._lock:
            if cls._cache is None:
                return {
                    "cached": False,
                    "cache_age": None,
                    "ttl": cls._cache_ttl,
                    "shared": True
                }
            
            current_time = time.time()
            cache_age = current_time - cls._cache_time if cls._cache_time else None
            
            return {
                "cached": True,
                "cache_age_seconds": cache_age,
                "ttl_seconds": cls._cache_ttl,
                "is_stale": cache_age > cls._cache_ttl if cache_age else False,
                "couriers_count": len(cls._cache.get("couriers", {})),
                "shared": True
            }