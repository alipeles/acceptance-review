def format_total(amount):
    return f"${amount:.2f}"


def checkout(items):
    subtotal = sum(item["price"] for item in items)
    return format_total(subtotal)


def apply_discount(cart, percent):
    raise NotImplementedError
