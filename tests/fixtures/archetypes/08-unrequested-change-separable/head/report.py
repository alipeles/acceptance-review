def low_stock_report(inventory, threshold):
    return [item for item in inventory if item["qty"] < threshold]
