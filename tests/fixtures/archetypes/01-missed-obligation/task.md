# Task
Implement `format_line(name, quantity, unit_price)` in `receipt.py`, returning a
single formatted line string.

## Constraints
- Show the item name, the quantity, and the unit price.
- Include the line total (quantity × unit price).
- Format every money value as USD with exactly two decimals and a leading `$`.
- For returns (a negative quantity), show the quantity and the line total in
  parentheses rather than with a minus sign — e.g. `(2)` and `($5.00)`.
