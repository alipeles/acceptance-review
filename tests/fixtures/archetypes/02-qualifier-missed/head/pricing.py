SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}


def parse_price(text):
    symbol = text[0]
    return float(text[1:]), SYMBOLS[symbol]
