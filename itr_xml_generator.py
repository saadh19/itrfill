import xml.etree.ElementTree as ET
import os

def generate_itr1_xml(form16_data, answers, tax_result):
    ay = form16_data.get("assessment_year", "2025-26")
    regime = tax_result["recommended"]

    root = ET.Element("ITR")
    root.set("xmlns", "http://incometaxindiaefiling.gov.in/master")
    itr1 = ET.SubElement(root, "ITR1")

    # Personal Info
    personal = ET.SubElement(itr1, "PersonalInfo")
    ET.SubElement(personal, "AssesseeName").text = str(form16_data.get("employee_name", ""))
    ET.SubElement(personal, "PAN").text = str(form16_data.get("pan_number", "")).upper()
    ET.SubElement(personal, "AssessmentYear").text = str(ay)
    ET.SubElement(personal, "FilingStatus").text = "O"
    ET.SubElement(personal, "ResidentialStatus").text = "RES"

    # Bank details for refund
    bank_str = str(answers.get("bank_details", ""))
    bank_parts = bank_str.split()
    if len(bank_parts) >= 2:
        bank = ET.SubElement(itr1, "Refund")
        ET.SubElement(bank, "BankAccountNo").text = bank_parts[0]
        ET.SubElement(bank, "IFSCCode").text = bank_parts[1].upper()
        ET.SubElement(bank, "BankName").text = "Bank"
        ET.SubElement(bank, "AccountType").text = "SB"

    # Income and Deductions
    income = ET.SubElement(itr1, "IncomeDeductions")
    ET.SubElement(income, "GrossSalary").text = str(form16_data.get("gross_salary", 0))
    ET.SubElement(income, "HRAExemption").text = str(form16_data.get("hra_exemption", 0))
    ET.SubElement(income, "StandardDeduction").text = "50000"
    ET.SubElement(income, "ProfessionalTax").text = str(form16_data.get("professional_tax", 0))
    ET.SubElement(income, "Section80C").text = str(
        form16_data.get("section_80c", 0) + int(answers.get("extra_80c", 0) or 0)
    )
    ET.SubElement(income, "Section80D").text = str(
        form16_data.get("section_80d", 0) + int(answers.get("extra_80d", 0) or 0)
    )
    ET.SubElement(income, "Section80CCD").text = str(form16_data.get("nps_80ccd", 0))
    ET.SubElement(income, "OtherIncome").text = str(answers.get("other_income", 0) or 0)

    # Tax Details
    tax_info = ET.SubElement(itr1, "TaxDetails")
    ET.SubElement(tax_info, "TaxRegime").text = "NEW" if regime == "new" else "OLD"
    ET.SubElement(tax_info, "TaxPayable").text = str(tax_result[f"{regime}_regime"]["tax_liability"])
    ET.SubElement(tax_info, "TDSDeducted").text = str(form16_data.get("total_tds_deducted", 0))
    ET.SubElement(tax_info, "EmployerTAN").text = str(form16_data.get("employer_tan", ""))

    refund = tax_result[f"{regime}_regime"]["refund_or_due"]
    if refund > 0:
        ET.SubElement(tax_info, "Refund").text = str(refund)
        ET.SubElement(tax_info, "TaxDue").text = "0"
    else:
        ET.SubElement(tax_info, "Refund").text = "0"
        ET.SubElement(tax_info, "TaxDue").text = str(abs(refund))

    # Write XML file
    os.makedirs("outputs", exist_ok=True)
    pan = form16_data.get("pan_number", "USER").upper()
    filename = f"outputs/ITR1_{pan}_{ay}.xml"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(filename, encoding="utf-8", xml_declaration=True)

    return filename
