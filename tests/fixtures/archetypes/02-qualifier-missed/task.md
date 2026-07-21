# Task: Add currency support to price parsing

Extend `parse_price(text)` in `pricing.py` to accept an optional leading
currency symbol and return `(amount, currency_code)`.

Requirements:

1. Parse a leading currency symbol into its ISO code: `$` → `USD`, `£` → `GBP`,
   `€` → `EUR`.
2. Parse the remaining numeric amount as a float.
3. Existing callers pass plain numeric strings with no symbol; those must keep
   working and default to `USD`.
