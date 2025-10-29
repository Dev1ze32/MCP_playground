from fastmcp import FastMCP
from datetime import datetime, timedelta
import pytz
import logging
import time

# Import our modules
from models import ErrorCode, DeliveryEstimate
from config import ConfigCache
from validators import InputValidator
from calculator import DeliveryCalculator

# LOGGING CONFIGURATION

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# INITIALIZE MCP SERVER

mcp = FastMCP("Delivery Estimation Service")

# MCP TOOLS

@mcp.tool()
def delivery_estimate(courier_name: str, region: str) -> dict:
    """
    Estimate delivery date for an order based on courier and region.
    
    Returns:
        Dictionary containing delivery estimation details or error information
    """
    request_id = f"{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Delivery estimate request: courier={courier_name}, region={region}")
    
    try:
        # Step 1: Validate inputs
        courier_valid, courier_normalized, courier_error = InputValidator.validate_courier(courier_name)
        if not courier_valid:
            logger.warning(f"[{request_id}] Invalid courier: {courier_error}")
            return {
                "error": courier_error,
                "error_code": ErrorCode.INVALID_COURIER.value
            }
        
        region_valid, region_normalized, region_error = InputValidator.validate_region(region)
        if not region_valid:
            logger.warning(f"[{request_id}] Invalid region: {region_error}")
            return {
                "error": region_error,
                "error_code": ErrorCode.INVALID_REGION.value
            }
        
        # Step 2: Load configuration
        try:
            config = ConfigCache.get_config()
            if not config:
                raise ValueError("Configuration is None")
        except Exception as e:
            logger.error(f"[{request_id}] Configuration error: {str(e)}")
            return {
                "error": "Service temporarily unavailable. Please try again later.",
                "error_code": ErrorCode.CONFIG_ERROR.value
            }
        
        # Step 3: Get current time
        current_time = DeliveryCalculator.get_current_datetime(config["timezone"])
        if not current_time:
            logger.error(f"[{request_id}] Could not get current time")
            return {
                "error": "Internal error processing request",
                "error_code": ErrorCode.INTERNAL_ERROR.value
            }
        
        # Step 4: Check cutoff time
        is_before_cutoff = DeliveryCalculator.check_cutoff_time(
            current_time, 
            config["cutoff_time"]
        )
        
        # Step 5: Get base delivery days
        base_days = DeliveryCalculator.get_courier_base_days(
            config, 
            courier_normalized, 
            region_normalized
        )
        
        if base_days is None:
            logger.warning(f"[{request_id}] Courier or region not supported")
            return {
                "error": f"Courier '{courier_normalized}' does not service region '{region_normalized}'",
                "error_code": ErrorCode.INVALID_COURIER.value,
                "available_couriers": list(config["couriers"].keys())
            }
        
        # Step 6: Determine start date
        if is_before_cutoff:
            start_date = current_time.date()
            processing_note = "Order placed before cutoff - same day processing"
        else:
            start_date = current_time.date() + timedelta(days=1)
            processing_note = "Order placed after cutoff - next day processing"
        
        # Step 7: Calculate delivery date
        estimated_delivery = DeliveryCalculator.calculate_delivery_date(
            start_date,
            base_days,
            courier_normalized
        )
        
        if not estimated_delivery:
            logger.error(f"[{request_id}] Could not calculate delivery date")
            return {
                "error": "Unable to calculate delivery date",
                "error_code": ErrorCode.INTERNAL_ERROR.value
            }
        
        # Step 8: Build response
        result = DeliveryEstimate(
            courier=courier_normalized,
            region=region_normalized,
            order_time=current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            cutoff_time=config["cutoff_time"],
            before_cutoff=is_before_cutoff,
            processing_note=processing_note,
            start_date=start_date.strftime('%Y-%m-%d'),
            base_delivery_days=base_days,
            estimated_delivery_date=estimated_delivery.strftime('%Y-%m-%d'),
            total_calendar_days=(estimated_delivery - start_date).days,
            confidence_level="high"
        )
        
        logger.info(f"[{request_id}] Delivery estimate completed: {estimated_delivery}")
        
        return result.to_dict()
        
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error in delivery_estimate")
        return {
            "error": "An unexpected error occurred",
            "error_code": ErrorCode.INTERNAL_ERROR.value
        }


@mcp.tool()
def health_check() -> dict:
    """
    Health check endpoint for monitoring
    
    Returns:
        Dictionary with service health status
    """
    try:
        # Check if configuration is loadable
        config = ConfigCache.get_config()
        config_status = "ok" if config else "error"
        
        # Check current time retrieval
        current_time = DeliveryCalculator.get_current_datetime()
        time_status = "ok" if current_time else "error"
        
        overall_status = "healthy" if (config_status == "ok" and time_status == "ok") else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "checks": {
                "configuration": config_status,
                "time_service": time_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "error": str(e)
        }


@mcp.tool()
def refresh_config() -> dict:
    """
    Manually refresh configuration cache
    
    Returns:
        Dictionary with refresh status
    """
    try:
        logger.info("Manual configuration refresh requested")
        config = ConfigCache.get_config(force_refresh=True)
        
        return {
            "status": "success",
            "message": "Configuration refreshed successfully",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "couriers": list(config["couriers"].keys()) if config else []
        }
    except Exception as e:
        logger.error(f"Configuration refresh failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to refresh configuration: {str(e)}",
            "timestamp": datetime.now(pytz.UTC).isoformat()
        }


@mcp.tool()
def list_available_services() -> dict:
    """
    List all available couriers and regions
    
    Returns:
        Dictionary with available services
    """
    try:
        config = ConfigCache.get_config()
        
        if not config:
            return {
                "error": "Configuration not available",
                "error_code": ErrorCode.CONFIG_ERROR.value
            }
        
        services = {}
        for courier, regions in config["couriers"].items():
            services[courier] = {
                "regions": list(regions.keys()),
                "delivery_days": regions
            }
        
        return {
            "status": "success",
            "cutoff_time": config["cutoff_time"],
            "timezone": config["timezone"],
            "couriers": services,
            "allowed_regions": InputValidator.ALLOWED_REGIONS
        }
        
    except Exception as e:
        logger.error(f"Error listing services: {str(e)}")
        return {
            "error": "Unable to retrieve service information",
            "error_code": ErrorCode.INTERNAL_ERROR.value
        }


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    logger.info("Starting Delivery Estimation Service")
    logger.info(f"Server will run on http://localhost:8080")
    
    try:
        # Preload configuration on startup
        config = ConfigCache.get_config()
        if config:
            logger.info(f"Configuration loaded: {len(config['couriers'])} couriers available")
        else:
            logger.warning("Failed to load initial configuration")
        
        mcp.run(transport="http")
        
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        raise
