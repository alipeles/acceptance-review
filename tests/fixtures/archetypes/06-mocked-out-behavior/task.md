# Task: Coupon uses the selected index rate

Implement `coupon(nominal, rate_source, date)` in `coupon.py`. It must select
the index rate for `date` by calling `rate_source.rate_for(date)`, then return
`nominal * selected_rate` rounded to four decimals. The core behavior under
review is that the rate chosen corresponds to the given `date`.
