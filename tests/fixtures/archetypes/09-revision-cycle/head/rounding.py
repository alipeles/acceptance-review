import math


def round_half_even(x):
    floor = math.floor(x)
    remainder = x - floor
    if remainder < 0.5:
        return floor
    if remainder > 0.5:
        return floor + 1
    # Exact tie: round to the even neighbour.
    return floor if floor % 2 == 0 else floor + 1
