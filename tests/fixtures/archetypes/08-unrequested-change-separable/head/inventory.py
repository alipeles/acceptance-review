def restock(item, qty):
    item["qty"] += qty
    return item["qty"]
