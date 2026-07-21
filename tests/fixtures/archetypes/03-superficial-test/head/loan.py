def amortize(principal, annual_rate, months):
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        payment = principal / months
    else:
        payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
    return [round(payment, 2) for _ in range(months)]
