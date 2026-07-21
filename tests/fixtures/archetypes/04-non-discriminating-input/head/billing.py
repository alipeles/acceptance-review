def prorate(monthly_price, days_used, days_in_month):
    daily_rate = monthly_price / days_in_month
    return round(daily_rate * days_used, 2)
