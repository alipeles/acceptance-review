from report import low_stock_report


def test_low_stock_report_filters_by_threshold():
    inventory = [{"qty": 2}, {"qty": 10}]
    assert low_stock_report(inventory, 5) == [{"qty": 2}]
