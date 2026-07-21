def apply_discount(total, percent):
    return round(total * (1 - percent / 100), 2)


def checkout(items, *, tax_rate=0.0):
    subtotal = sum(item["price"] for item in items)
    return round(subtotal * (1 + tax_rate), 2)
