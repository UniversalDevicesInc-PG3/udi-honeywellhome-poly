

def to_driver_value(temp, as_int=True):
    temp = float(temp)

    if as_int:
        return int(temp)
    else:
        return temp


def to_celsius(temp_fahrenheit):
    # Round to the nearest .5
    return round((temp_fahrenheit - 32) * 5 / 9)


def to_fahrenheit(temp_celsius):
    # Round to nearest whole degree
    return int(round(temp_celsius * 1.8) + 32)
