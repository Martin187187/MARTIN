from datetime import datetime, time
import calendar


def is_public_holiday(date):
    # Hardcoded list of public holidays (replace with an actual list or API call)
    public_holidays = [
        "2022-01-01",  # New Year's Day
        "2022-07-04",  # Independence Day
        # Add more holidays as needed
    ]

    # Convert date to datetime object if it's not already
    if not isinstance(date, datetime):
        date = datetime.strptime(date, '%Y-%m-%d')

    # Check if the day is a public holiday
    if date.strftime('%Y-%m-%d') in public_holidays:
        return True
    else:
        return False


def is_workday(date):
    # Check if the day is a Saturday or Sunday
    if date.weekday() >= 5:
        return False

    # Check if the day is a public holiday
    if is_public_holiday(date):
        return False

    return True


def is_in_time_interval(check_datetime: time, start_datetime: time, end_datetime: time):
    return start_datetime <= check_datetime < end_datetime
