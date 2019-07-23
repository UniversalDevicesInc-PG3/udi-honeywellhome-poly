

def to_driver_value(temp, as_int=True):
    if temp is None:
        return 0

    temp = float(temp)

    if as_int:
        return int(round(temp))
    else:
        return round(temp, 1)
