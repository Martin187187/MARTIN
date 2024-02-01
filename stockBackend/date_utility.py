from datetime import datetime, time, timedelta
from datetime import datetime, time, date
from typing import List


def is_public_holiday(value: date, public_holidays: List[date]):

    return value in public_holidays


def is_workday(value: date, public_holidays: List[date]):
    # Check if the day is a Saturday or Sunday
    if value.weekday() >= 5:
        return False

    # Check if the day is a public holiday
    return not is_public_holiday(value, public_holidays)


def is_in_time_interval(check_datetime: time, start_datetime: time, end_datetime: time):
    return start_datetime <= check_datetime < end_datetime


def time_until_next_workday_and_interval(current_datetime: datetime, public_holidays: List[date],
                                         start_datetime: time, end_datetime: time) -> timedelta:
    """
    Calculate the duration until the next workday within the specified time interval.
    """
    one_day = timedelta(days=1)

    if is_in_time_interval(current_datetime.time(), start_datetime, end_datetime):
        current_date = current_datetime
        while not is_workday(current_date, public_holidays):
            current_date += one_day
        return current_date - current_datetime
    else:
        next_workday_start = datetime.combine(current_datetime.date(), start_datetime)

        # Check if the calculated timedelta is negative
        while next_workday_start < current_datetime or not is_workday(next_workday_start.date(), public_holidays):
            # If negative, calculate the timedelta until the start of the next workday
            next_workday_start += timedelta(days=1)

        return next_workday_start - current_datetime

