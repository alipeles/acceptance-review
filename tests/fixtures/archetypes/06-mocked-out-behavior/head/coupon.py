def coupon(nominal, rate_source, date):
    rate = rate_source.rate_for(date)
    return round(nominal * rate, 4)
