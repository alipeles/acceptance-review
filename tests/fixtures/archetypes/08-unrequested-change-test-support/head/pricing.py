def line_total(item):
    subtotal = item["qty"] * item["price"]
    return round(subtotal * (1 - item["discount"] / 100), 2)
