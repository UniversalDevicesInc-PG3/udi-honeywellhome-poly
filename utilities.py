
from datetime import datetime


def to_driver_value(temp, as_int=True):
    if temp is None:
        return 0

    temp = float(temp)

    if as_int:
        return int(round(temp))
    else:
        return round(temp, 1)


def to_half(number):
    """Round a number to the closest half integer.
    round_of_rating(1.3)
    1.5
    round_of_rating(2.6)
    2.5
    round_of_rating(3.0)
    3.0
    round_of_rating(4.1)
    4.0"""

    return round(number * 2) / 2


def get_seconds_from_midnight():
    now = datetime.now()
    return (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
