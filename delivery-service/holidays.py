"""
holidays.py - Philippine Holiday Calculations
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)


class HolidayCalculator:
    """Handles Philippine holidays with caching"""
    
    _holiday_cache: Dict[int, List[datetime.date]] = {}
    _major_holiday_cache: Dict[int, List[datetime.date]] = {}
    
    @classmethod
    def _calculate_easter(cls, year: int) -> datetime.date:
        """
        Calculate Easter Sunday using Computus algorithm (Anonymous Gregorian algorithm)
        
        Args:
            year: Year to calculate Easter for
            
        Returns:
            Date of Easter Sunday
        """
        try:
            # Computus algorithm for Gregorian calendar
            a = year % 19
            b = year // 100
            c = year % 100
            d = b // 4
            e = b % 4
            f = (b + 8) // 25
            g = (b - f + 1) // 3
            h = (19 * a + b - d - g + 15) % 30
            i = c // 4
            k = c % 4
            l = (32 + 2 * e + 2 * i - h - k) % 7
            m = (a + 11 * h + 22 * l) // 451
            month = (h + l - 7 * m + 114) // 31
            day = ((h + l - 7 * m + 114) % 31) + 1
            
            easter = datetime(year, month, day).date()
            logger.debug(f"Easter {year}: {easter}")
            return easter
            
        except Exception as e:
            logger.error(f"Error calculating Easter for year {year}: {str(e)}")
            # Fallback to approximate date (mid-April)
            fallback = datetime(year, 4, 15).date()
            logger.warning(f"Using fallback Easter date: {fallback}")
            return fallback
    
    @classmethod
    def _get_holy_week_dates(cls, year: int) -> List[datetime.date]:
        """
        Get Holy Week dates based on Easter calculation
        
        Args:
            year: Year to get Holy Week dates for
            
        Returns:
            List of Holy Week dates [Maundy Thursday, Good Friday, Black Saturday]
        """
        try:
            easter_sunday = cls._calculate_easter(year)
            maundy_thursday = easter_sunday - timedelta(days=3)
            good_friday = easter_sunday - timedelta(days=2)
            black_saturday = easter_sunday - timedelta(days=1)
            
            logger.debug(f"Holy Week {year}: {maundy_thursday}, {good_friday}, {black_saturday}")
            return [maundy_thursday, good_friday, black_saturday]
            
        except Exception as e:
            logger.error(f"Error calculating Holy Week for year {year}: {str(e)}")
            return []
    
    @classmethod
    def get_ph_holidays(cls, year: int) -> List[datetime.date]:
        """
        Get all Philippine regular holidays for a year (cached)
        
        NOTE: This includes fixed holidays. Government may declare additional
        special non-working days or move holidays via proclamation.
        
        Args:
            year: Year to get holidays for
            
        Returns:
            List of holiday dates
        """
        # Return cached result if available
        if year in cls._holiday_cache:
            logger.debug(f"Using cached holidays for {year}")
            return cls._holiday_cache[year]
        
        try:
            holidays = [
                datetime(year, 1, 1).date(),   # New Year's Day
                datetime(year, 4, 9).date(),   # Araw ng Kagitingan (Day of Valor)
                datetime(year, 5, 1).date(),   # Labor Day
                datetime(year, 6, 12).date(),  # Independence Day
                datetime(year, 8, 21).date(),  # Ninoy Aquino Day (Special)
                datetime(year, 8, 25).date(),  # National Heroes Day (Last Monday of August - approximate)
                datetime(year, 11, 1).date(),  # All Saints' Day
                datetime(year, 11, 30).date(), # Bonifacio Day
                datetime(year, 12, 25).date(), # Christmas Day
                datetime(year, 12, 30).date(), # Rizal Day
                datetime(year, 12, 31).date(), # Last Day of the Year (Special)
            ]
            
            # Add movable Holy Week holidays
            holy_week = cls._get_holy_week_dates(year)
            holidays.extend(holy_week)
            
            # Remove duplicates and sort
            holidays = sorted(list(set(holidays)))
            
            # Cache the result
            cls._holiday_cache[year] = holidays
            logger.info(f"Cached {len(holidays)} holidays for year {year}")
            
            return holidays
            
        except Exception as e:
            logger.error(f"Error getting holidays for year {year}: {str(e)}")
            return []
    
    @classmethod
    def get_major_ph_holidays(cls, year: int) -> List[datetime.date]:
        """
        Get major Philippine holidays (when most courier services don't operate)
        
        Args:
            year: Year to get major holidays for
            
        Returns:
            List of major holiday dates
        """
        # Return cached result if available
        if year in cls._major_holiday_cache:
            logger.debug(f"Using cached major holidays for {year}")
            return cls._major_holiday_cache[year]
        
        try:
            holidays = [
                datetime(year, 1, 1).date(),   # New Year's Day
                datetime(year, 12, 25).date(), # Christmas Day
            ]
            
            # Add Maundy Thursday and Good Friday from Holy Week
            holy_week = cls._get_holy_week_dates(year)
            if len(holy_week) >= 2:
                holidays.extend([holy_week[0], holy_week[1]])  # Maundy Thursday, Good Friday
            
            # Remove duplicates and sort
            holidays = sorted(list(set(holidays)))
            
            # Cache the result
            cls._major_holiday_cache[year] = holidays
            logger.info(f"Cached {len(holidays)} major holidays for year {year}")
            
            return holidays
            
        except Exception as e:
            logger.error(f"Error getting major holidays for year {year}: {str(e)}")
            return []
    
    @classmethod
    def is_holiday(cls, date: datetime.date, major_only: bool = False) -> bool:
        """
        Check if a date is a holiday
        
        Args:
            date: Date to check
            major_only: If True, only check major holidays
            
        Returns:
            True if the date is a holiday
        """
        year = date.year
        
        if major_only:
            holidays = cls.get_major_ph_holidays(year)
        else:
            holidays = cls.get_ph_holidays(year)
        
        return date in holidays
    
    @classmethod
    def is_weekend(cls, date: datetime.date) -> bool:
        """
        Check if a date is a weekend (Saturday or Sunday)
        
        Args:
            date: Date to check
            
        Returns:
            True if the date is a weekend
        """
        return date.weekday() in [5, 6]  # Saturday=5, Sunday=6
    
    @classmethod
    def is_sunday(cls, date: datetime.date) -> bool:
        """
        Check if a date is a Sunday
        
        Args:
            date: Date to check
            
        Returns:
            True if the date is a Sunday
        """
        return date.weekday() == 6
    
    @classmethod
    def clear_cache(cls):
        """Clear holiday cache (useful for testing or year rollover)"""
        cls._holiday_cache.clear()
        cls._major_holiday_cache.clear()
        logger.info("Holiday cache cleared")
    
    @classmethod
    def get_next_working_day(cls, date: datetime.date, major_holidays_only: bool = False) -> datetime.date:
        """
        Get the next working day after a given date
        
        Args:
            date: Starting date
            major_holidays_only: If True, only skip major holidays
            
        Returns:
            Next working day
        """
        next_day = date + timedelta(days=1)
        max_iterations = 30  # Prevent infinite loop
        iterations = 0
        
        while iterations < max_iterations:
            if not cls.is_sunday(next_day) and not cls.is_holiday(next_day, major_holidays_only):
                return next_day
            next_day += timedelta(days=1)
            iterations += 1
        
        logger.warning(f"Max iterations reached finding next working day after {date}")
        return next_day