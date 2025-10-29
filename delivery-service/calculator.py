"""
calculator.py - Delivery Date Calculations
"""

import logging
import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional
from holidays import HolidayCalculator

logger = logging.getLogger(__name__)


class DeliveryCalculator:
    """Handles delivery date calculations with business logic"""
    
    # Maximum iterations to prevent infinite loops
    MAX_CALCULATION_ITERATIONS = 100
    
    @staticmethod
    def get_current_datetime(timezone: str = "Asia/Manila") -> Optional[datetime]:
        """
        Get current datetime in specified timezone with error handling
        
        Args:
            timezone: Timezone string (e.g., "Asia/Manila")
            
        Returns:
            Current datetime in specified timezone, or UTC as fallback
        """
        try:
            tz = pytz.timezone(timezone)
            current = datetime.now(tz)
            logger.debug(f"Current time in {timezone}: {current}")
            return current
            
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone}, falling back to UTC")
            return datetime.now(pytz.UTC)
            
        except Exception as e:
            logger.error(f"Error getting current datetime for timezone {timezone}: {str(e)}")
            # Fallback to UTC
            return datetime.now(pytz.UTC)
    
    @staticmethod
    def check_cutoff_time(current_time: datetime, cutoff_time: str) -> bool:
        """
        Check if current time is before cutoff time
        
        Args:
            current_time: Current datetime with timezone
            cutoff_time: Cutoff time string in HH:MM format
            
        Returns:
            True if current time is before cutoff, False otherwise
        """
        try:
            cutoff_hour, cutoff_min = map(int, cutoff_time.split(':'))
            
            # Create cutoff datetime for today
            cutoff_dt = current_time.replace(
                hour=cutoff_hour, 
                minute=cutoff_min, 
                second=0, 
                microsecond=0
            )
            
            is_before = current_time < cutoff_dt
            logger.debug(
                f"Cutoff check: current={current_time.strftime('%H:%M:%S')}, "
                f"cutoff={cutoff_time}, before_cutoff={is_before}"
            )
            
            return is_before
            
        except ValueError as e:
            logger.error(f"Invalid cutoff time format '{cutoff_time}': {str(e)}")
            # Default to after cutoff if error (safer)
            return False
            
        except Exception as e:
            logger.error(f"Error checking cutoff time: {str(e)}")
            # Default to after cutoff if error
            return False
    
    @staticmethod
    def get_courier_base_days(
        config: Dict, 
        courier_name: str, 
        region: str
    ) -> Optional[int]:
        """
        Get base delivery days for courier and region from configuration
        
        Args:
            config: Configuration dictionary
            courier_name: Courier name (should be normalized)
            region: Region name (should be normalized)
            
        Returns:
            Base delivery days as integer, or None if not found/invalid
        """
        try:
            # Check if courier exists in config
            if courier_name not in config["couriers"]:
                logger.warning(f"Courier '{courier_name}' not found in configuration")
                logger.debug(f"Available couriers: {list(config['couriers'].keys())}")
                return None
            
            courier_data = config["couriers"][courier_name]
            
            # Check if region exists for this courier
            if region not in courier_data:
                logger.warning(
                    f"Region '{region}' not found for courier '{courier_name}'. "
                    f"Available regions: {list(courier_data.keys())}"
                )
                return None
            
            base_days = courier_data[region]
            
            # Validate base_days is a positive integer
            if not isinstance(base_days, int):
                logger.error(f"Invalid base_days type for {courier_name}/{region}: {type(base_days)}")
                return None
            
            if base_days <= 0:
                logger.error(f"Invalid base_days value for {courier_name}/{region}: {base_days}")
                return None
            
            logger.debug(f"Base delivery days for {courier_name}/{region}: {base_days}")
            return base_days
            
        except KeyError as e:
            logger.error(f"Missing key in configuration: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting base delivery days: {str(e)}")
            return None
    
    @staticmethod
    def should_skip_date(courier_name: str, date: datetime.date) -> bool:
        """
        Check if a date should be skipped for delivery based on courier policy
        
        Different couriers have different operating schedules:
        - LBC: Skips all Sundays and all PH holidays
        - J&T: Only skips major holidays (New Year, Christmas, Holy Week)
        - Others: Default to skipping Sundays and all holidays
        
        Args:
            courier_name: Courier name (normalized)
            date: Date to check
            
        Returns:
            True if date should be skipped, False if it's a valid delivery day
        """
        try:
            is_sunday = HolidayCalculator.is_sunday(date)
            year = date.year
            
            # Courier-specific logic
            if courier_name == "LBC":
                # LBC doesn't deliver on Sundays or any PH holidays
                is_holiday = HolidayCalculator.is_holiday(date, major_only=False)
                should_skip = is_sunday or is_holiday
                
                if should_skip:
                    logger.debug(f"LBC skipping {date}: sunday={is_sunday}, holiday={is_holiday}")
                
                return should_skip
            
            elif courier_name == "J&T":
                # J&T operates on most days, only skips major holidays
                is_major_holiday = HolidayCalculator.is_holiday(date, major_only=True)
                
                if is_major_holiday:
                    logger.debug(f"J&T skipping {date}: major holiday")
                
                return is_major_holiday
            
            else:
                # Default behavior for other couriers
                is_holiday = HolidayCalculator.is_holiday(date, major_only=False)
                should_skip = is_sunday or is_holiday
                
                if should_skip:
                    logger.debug(f"{courier_name} skipping {date}: sunday={is_sunday}, holiday={is_holiday}")
                
                return should_skip
                
        except Exception as e:
            logger.error(f"Error checking skip date for {courier_name} on {date}: {str(e)}")
            # Default to not skipping if error (safer to over-deliver)
            return False
    
    @staticmethod
    def calculate_delivery_date(
        start_date: datetime.date,
        base_days: int,
        courier_name: str,
        max_iterations: Optional[int] = None
    ) -> Optional[datetime.date]:
        """
        Calculate delivery date by adding business days and skipping holidays
        
        Args:
            start_date: Starting date for calculation (processing start date)
            base_days: Number of business days for delivery
            courier_name: Courier name for skip logic
            max_iterations: Maximum iterations to prevent infinite loop
            
        Returns:
            Estimated delivery date, or None if calculation fails
        """
        if max_iterations is None:
            max_iterations = DeliveryCalculator.MAX_CALCULATION_ITERATIONS
        
        try:
            if base_days <= 0:
                logger.error(f"Invalid base_days: {base_days}")
                return None
            
            days_added = 0
            current_date = start_date
            iterations = 0
            
            logger.debug(
                f"Calculating delivery: start={start_date}, "
                f"base_days={base_days}, courier={courier_name}"
            )
            
            # Add business days while skipping non-delivery days
            while days_added < base_days and iterations < max_iterations:
                current_date += timedelta(days=1)
                iterations += 1
                
                # Check if this day counts as a delivery day
                if not DeliveryCalculator.should_skip_date(courier_name, current_date):
                    days_added += 1
                    logger.debug(f"Day {days_added}/{base_days}: {current_date}")
            
            # Check if we hit max iterations
            if iterations >= max_iterations:
                logger.error(
                    f"Max iterations ({max_iterations}) reached calculating delivery date. "
                    f"Start: {start_date}, Base days: {base_days}"
                )
                return None
            
            logger.info(
                f"Delivery calculation complete: {start_date} + {base_days} days = {current_date} "
                f"({iterations} calendar days, {courier_name})"
            )
            
            return current_date
            
        except Exception as e:
            logger.error(f"Error calculating delivery date: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def get_delivery_confidence(
        base_days: int,
        total_calendar_days: int,
        courier_name: str
    ) -> str:
        """
        Calculate confidence level for delivery estimate
        
        Args:
            base_days: Base delivery days
            total_calendar_days: Actual calendar days until delivery
            courier_name: Courier name
            
        Returns:
            Confidence level: "high", "medium", or "low"
        """
        try:
            # If calendar days is much longer than base days, lower confidence
            day_ratio = total_calendar_days / base_days if base_days > 0 else 1
            
            if day_ratio <= 1.5:
                confidence = "high"
            elif day_ratio <= 2.0:
                confidence = "medium"
            else:
                confidence = "low"
            
            logger.debug(
                f"Confidence calculation: base={base_days}, calendar={total_calendar_days}, "
                f"ratio={day_ratio:.2f}, confidence={confidence}"
            )
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return "medium"