def _apply_tax(subtotal, tax_rate):
    return subtotal * (1 + tax_rate)


def order_total(subtotal, tax_rate):
    return round(_apply_tax(subtotal, tax_rate), 2)
