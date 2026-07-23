def format_total(amount, currency="USD"):
    symbol = "$" if currency == "USD" else currency + " "
    return f"{symbol}{amount:.2f}"


def checkout(items):
    subtotal = sum(item["price"] for item in items)
    return format_total(subtotal)


def apply_discount(cart, percent, currency="USD"):
    subtotal = sum(item["price"] for item in cart)
    discounted = subtotal * (1 - percent / 100)
    return format_total(discounted, currency)
