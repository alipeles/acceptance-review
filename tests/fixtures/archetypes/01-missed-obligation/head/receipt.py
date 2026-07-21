def format_line(name, quantity, unit_price):
    total = quantity * unit_price
    return f"{name} x{quantity} @ ${unit_price:.2f} = ${total:.2f}"
