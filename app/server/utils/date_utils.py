import datetime
from datetime import timedelta, timezone


def has_expired(expiry: int) -> bool:
    """
    Checks if the given expiry timestamp has already passed.

    Args:
        expiry: The expiry timestamp to check.
    Returns:
        True if the expiry timestamp has already passed, False otherwise.
    """

    return expiry <= get_current_timestamp()


def get_current_timestamp() -> int:
    """
    Returns the current Unix timestamp in milliseconds.

    Returns:
        An integer representing the current Unix timestamp in milliseconds.
    """

    # Get the current timezone-aware datetime object in UTC
    current_time = datetime.datetime.now(timezone.utc)

    # Get the Unix epoch timestamp in seconds
    timestamp_seconds = current_time.timestamp()

    return int(timestamp_seconds * 1000)


def get_current_timestamp_in_seconds() -> datetime.datetime:
    """
    Returns the current UTC datetime.

    Returns:
        A datetime object representing the current time in UTC.
    """
    return datetime.datetime.now(timezone.utc)


def get_timestamp(expires_delta: timedelta = timedelta(hours=1)) -> int:
    """
    Generates a Unix epoch timestamp in milliseconds, given an optional time delta.

    Args:
        expires_delta: A timedelta object representing the time delta to add to the current time. Defaults to 1 hour.
    Returns:
        An integer representing the Unix epoch timestamp in milliseconds.
    """

    # Get the current timezone-aware datetime object in UTC
    current_time = datetime.datetime.now(timezone.utc)
    current_time = current_time + expires_delta

    # Get the Unix epoch timestamp in seconds
    timestamp_seconds = current_time.timestamp()

    return int(timestamp_seconds * 1000)


def get_current_date_time() -> datetime.datetime:
    """
    Returns the current date and time in UTC timezone.

    Returns:
        A datetime object representing the current date and time in UTC timezone.
    """

    return datetime.datetime.now(timezone.utc)


def get_n_previous_day_timestamp(days) -> int:
    """
    Returns the UNIX timestamp in milliseconds of `days` number of days ago at midnight UTC.

    Args:
        days: The number of days ago to retrieve the timestamp for.
    Returns:
        The timestamp in milliseconds.
    """

    prev_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=days)
    midnight_prev_time = datetime.datetime.combine(prev_time, datetime.time.min)
    midnight_prev_time = midnight_prev_time.replace(tzinfo=timezone.utc)
    return int(midnight_prev_time.timestamp() * 1000)


def get_today_midnight_time() -> int:
    """
    Get the timestamp in milliseconds of the current day at midnight.

    Returns:
        The timestamp of the current day at midnight.
    """

    now = datetime.datetime.now(tz=timezone.utc)
    midnight_date = datetime.datetime.combine(now, datetime.time.min)  # Midnight
    midnight_date = midnight_date.replace(tzinfo=timezone.utc)
    return int(midnight_date.timestamp() * 1000)


def date_to_milliseconds(date_string: str, date_format: str = '%d-%m-%Y') -> int:
    """
    Convert a date string to milliseconds.
    Args:
        date_string: The input date string.
        date_format: The format of the input date string. Defaults to '%d-%m-%Y'.
    Returns:
        The date in milliseconds.
    """

    # Create a datetime object from the date string
    date_object = datetime.datetime.strptime(date_string, date_format)

    # Set the time to 00:00:00 and set the timezone to UTC
    date_object = datetime.datetime.combine(date_object, datetime.time.min)

    date_object = date_object.replace(tzinfo=timezone.utc)

    # Get the Unix epoch timestamp in seconds
    timestamp_seconds = date_object.timestamp()

    # Convert seconds to milliseconds and return
    return int(timestamp_seconds * 1000)


def get_future_end_of_day_timestamp(days: int, existing_timestamp: int = None) -> int:
    """Get the UNIX timestamp in milliseconds of `days` number of days in the future at midnight UTC.

    Args:
        days (int): The number of days in the future to retrieve the timestamp for.
        existing_timestamp (int, optional): The existing timestamp in milliseconds. Defaults to None.

    Returns:
        int: The timestamp in milliseconds.
    """
    # Convert existing timestamp from milliseconds to seconds
    if existing_timestamp is not None:
        current_timestamp = datetime.datetime.utcfromtimestamp(existing_timestamp / 1000)
    else:
        current_timestamp = datetime.datetime.now(timezone.utc)

    # Calculate future time by adding specified number of days to current timestamp
    future_time = current_timestamp + datetime.timedelta(days=days)

    # Set future time to the last second of the day
    midnight_future_time = datetime.datetime.combine(future_time, datetime.time.max)

    # Convert future time to UTC timezone
    midnight_future_time_utc = midnight_future_time.replace(tzinfo=timezone.utc)

    # Convert future time to timestamp in milliseconds
    return int(midnight_future_time_utc.timestamp() * 1000)


def get_future_start_of_day_timestamp(days: int, existing_timestamp: int = None) -> int:
    """
    Returns the UNIX timestamp in milliseconds of `days` number of days ago at midnight UTC.

    This function calculates the UNIX timestamp of a specific date in the future. The date is calculated
    by adding `days` to the current date or the date provided in `existing_timestamp`. The timestamp
    returned represents the start of that day (midnight).

    Args:
        days (int): The number of days in the future from the current date or the date provided in
                    `existing_timestamp` to retrieve the timestamp for.
        existing_timestamp (int, optional): The existing timestamp in milliseconds. If provided,
                                             the calculation will be based on this timestamp instead
                                             of the current date. Defaults to None.

    Returns:
        int: The UNIX timestamp in milliseconds representing the start of the specified date.
    """
    if existing_timestamp is not None:
        current_timestamp = datetime.datetime.utcfromtimestamp(existing_timestamp / 1000)
    else:
        current_timestamp = datetime.datetime.now(timezone.utc)

    prev_time = current_timestamp + datetime.timedelta(days=days)
    midnight_prev_time = datetime.datetime.combine(prev_time, datetime.time.min)
    midnight_prev_time = midnight_prev_time.replace(tzinfo=timezone.utc)
    return int(midnight_prev_time.timestamp() * 1000)


def get_date_from_timestamp(timestamp: int, tz_info=None):
    """
    Returns the datetime date object from a timestamp for a given timezone

    timestamp: Unix epoch timestamp
    tz: pytz timezone object

    """
    return datetime.datetime.fromtimestamp(timestamp / 1000, tz=tz_info).date()


def get_current_datetime_from_timezone(tz_info=None):
    """
    Returns current date object for a particular timezone

    tz: pytz timezone object
    """
    return datetime.datetime.now(tz=tz_info)


def get_future_timestamp_n_days(existing_timestamp: int, days: int):
    """
    Returns the UNIX timestamp in milliseconds of `days` number of days in the future from the existing timestamp in milliseconds
    """
    return existing_timestamp + (days * 24 * 60 * 60 * 1000)


def get_current_start_of_day_timestamp(tz_info=None):
    """
    Returns the UNIX timestamp in milliseconds of the current day at midnight
    """
    return int(get_current_datetime_from_timezone(tz_info=tz_info).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
