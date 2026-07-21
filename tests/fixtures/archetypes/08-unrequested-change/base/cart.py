def checkout(items):
    return sum(item["price"] for item in items)
