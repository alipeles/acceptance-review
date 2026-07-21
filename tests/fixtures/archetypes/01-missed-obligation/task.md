# Task: Receipt line formatter

Implement `format_line(name, quantity, unit_price)` in `receipt.py`, returning a
single formatted line string.

Requirements:

1. Show the item name, the quantity, and the unit price.
2. Include the line total (quantity × unit price).
3. Format every money value as USD with exactly two decimals and a leading `$`.
4. For returns (a negative quantity), show the quantity and the line total in
   parentheses rather than with a minus sign — e.g. `(2)` and `($5.00)`.
