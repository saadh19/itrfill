def calculate_tax_old_regime(taxable_income):
    tax = 0
    if taxable_income <= 250000:
        tax = 0
    elif taxable_income <= 500000:
        tax = (taxable_income - 250000) * 0.05
    elif taxable_income <= 1000000:
        tax = 12500 + (taxable_income - 500000) * 0.20
    else:
        tax = 112500 + (taxable_income - 1000000) * 0.30
    # Rebate u/s 87A - if income <= 5L, tax = 0
    if taxable_income <= 500000:
        tax = 0
    cess = tax * 0.04
    return round(tax + cess)

def calculate_tax_new_regime(taxable_income):
    tax = 0
    if taxable_income <= 300000:
        tax = 0
    elif taxable_income <= 600000:
        tax = (taxable_income - 300000) * 0.05
    elif taxable_income <= 900000:
        tax = 15000 + (taxable_income - 600000) * 0.10
    elif taxable_income <= 1200000:
        tax = 45000 + (taxable_income - 900000) * 0.15
    elif taxable_income <= 1500000:
        tax = 90000 + (taxable_income - 1200000) * 0.20
    else:
        tax = 150000 + (taxable_income - 1500000) * 0.30
    # Rebate u/s 87A - if income <= 7L, tax = 0
    if taxable_income <= 700000:
        tax = 0
    cess = tax * 0.04
    return round(tax + cess)

def compare_regimes(form16_data, extra_deductions={}):
    gross = form16_data.get("gross_salary", 0)

    # Old regime deductions
    old_deductions = (
        form16_data.get("hra_exemption", 0) +
        form16_data.get("standard_deduction", 50000) +
        form16_data.get("professional_tax", 0) +
        form16_data.get("section_80c", 0) +
        form16_data.get("section_80d", 0) +
        form16_data.get("nps_80ccd", 0) +
        extra_deductions.get("home_loan_interest", 0) +
        extra_deductions.get("rent_paid", 0) +
        extra_deductions.get("extra_80c", 0) +
        extra_deductions.get("extra_80d", 0)
    )

    # New regime - only standard deduction of 75000
    old_taxable = max(0, gross - old_deductions)
    new_taxable = max(0, gross - 75000)

    old_tax = calculate_tax_old_regime(old_taxable)
    new_tax = calculate_tax_new_regime(new_taxable)

    tds = form16_data.get("total_tds_deducted", 0)

    return {
        "old_regime": {
            "taxable_income": old_taxable,
            "tax_liability": old_tax,
            "refund_or_due": tds - old_tax
        },
        "new_regime": {
            "taxable_income": new_taxable,
            "tax_liability": new_tax,
            "refund_or_due": tds - new_tax
        },
        "recommended": "old" if old_tax < new_tax else "new",
        "savings": abs(old_tax - new_tax)
    }
