#!/usr/bin/env python3
"""
Cohezion Autonomous Credit Qualifier (v1.0)
Calculates loan capacity based on R&D tax assets and hardware collateral.
Target: TPU v7 (Ironwood) Expansion.
"""

import os


def calculate_qualification(annual_income, rd_spend_labor, hardware_cost):
    tax_rate = 0.37  # Assuming top bracket for optimization

    # 1. Immediate Expensing Benefit (Section 174A)
    # Total deduction = Labor + Hardware
    total_deduction = rd_spend_labor + hardware_cost
    tax_savings_174a = total_deduction * tax_rate

    # 2. R&D Tax Credit (Section 41) - Simplified Calculation
    # ~10% of qualified labor
    rd_credit = rd_spend_labor * 0.10

    # 3. Hardware Collateral Value (LTV ratio)
    # Ironwood v7 has high scarcity/utility; assuming 70% LTV
    hardware_collateral_value = hardware_cost * 0.70

    # 4. Total Loan Qualification
    # Lenders typically lend up to 80% of the 'Tax Asset' + Hardware Collateral
    loan_capacity = (tax_savings_174a * 0.90) + hardware_collateral_value + rd_credit

    return {
        "tax_savings_y1": round(tax_savings_174a, 2),
        "rd_credit_est": round(rd_credit, 2),
        "hardware_collateral": round(hardware_collateral_value, 2),
        "total_loan_qualification": round(loan_capacity, 2),
        "interest_coverage_ratio": round((annual_income / (loan_capacity * 0.08)), 2),  # 8% APR est
    }


def generate_report():
    # INPUTS: Adjust based on Cohezion mission
    LABOR = 150000  # Domestic R&D labor
    HARDWARE = 250000  # Pod of TPU v7 Ironwood Nodes
    INCOME = 300000  # Crypto Revenue + FT Income

    qual = calculate_qualification(INCOME, LABOR, HARDWARE)

    report = f"""
# COHEZION CREDIT QUALIFICATION REPORT
=======================================
[TARGET ASSET]: Google Cloud TPU v7 (Ironwood)
[FINANCING TYPE]: R&D-Backed Asset Loan (P.L. 119-21)

1. FISCAL RECOVERY (YEAR 1)
---------------------------
Immediate 174A Deduction:  ${qual["tax_savings_y1"]:,}
Estimated R&D Credit:      ${qual["rd_credit_est"]:,}
TOTAL TAX ASSET VALUE:     ${(qual["tax_savings_y1"] + qual["rd_credit_est"]):,}

2. COLLATERAL ANALYSIS
----------------------
TPU v7 Ironwood Val:       ${HARDWARE:,}
Lender Collateral (70%):   ${qual["hardware_collateral"]:,}

3. CAPACITY DETERMINATION
-------------------------
>>> TOTAL QUALIFIED LOAN:  ${qual["total_loan_qualification"]:,} <<<
Interest Coverage (8%):    {qual["interest_coverage_ratio"]}x

[CONCLUSION]: The tax recovery alone covers {round((qual["tax_savings_y1"] / (HARDWARE + LABOR)) * 100)}%
of the total investment principal in Year 1. This is a low-risk
autonomous credit event.
"""
    print(report)
    REPORT_PATH = "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/LOAN_QUALIFICATION.txt"
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)


if __name__ == "__main__":
    generate_report()
