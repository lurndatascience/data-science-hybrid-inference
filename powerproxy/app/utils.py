from datetime import datetime

def is_time_within_range(time_str, begin_utc="07:00", end_utc="17:00"):
    """
    Check if a given time is within a specified range.

    Parameters:
    - time_str (str): The time string to check in the format "%H:%M".
    - begin_utc (str): The beginning of the day in UTC time in the format "%H:%M". Default is "07:00".
    - end_utc (str): The end of the day in UTC time in the format "%H:%M". Default is "17:00".

    Returns:
    - bool: True if the input time is within the specified range, False otherwise.
    """
    # Parse the input time string
    input_time = datetime.strptime(time_str, "%H:%M").time()

    # Parse the day begin and end times
    day_begin = datetime.strptime(begin_utc, "%H:%M").time()
    day_end = datetime.strptime(end_utc, "%H:%M").time()

    # Check if the day end time is earlier than the day begin time (overflow case)
    if day_end < day_begin:
        # Check if the input time is within the overflow range
        return input_time >= day_begin or input_time <= day_end
    else:
        # Normal case
        return day_begin <= input_time <= day_end
