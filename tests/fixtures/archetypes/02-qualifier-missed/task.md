# Task
Extend `parse_price(text)` in `pricing.py` to accept an optional leading
currency symbol and return `(amount, currency_code)`.

## Constraints
- Parse a leading currency symbol into its ISO code: `$` → `USD`, `£` → `GBP`,
  `€` → `EUR`.
- Parse the remaining numeric amount as a float.
- Existing callers pass plain numeric strings with no symbol; those must keep
  working and default to `USD`.
