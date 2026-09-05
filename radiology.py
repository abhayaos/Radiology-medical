"""Radiology Medical - demo CLI built on the cpt.py billing engine."""

from cpt import (
    CPT_TABLES,
    RadiologyBilling,
    CptError,
    calculate_billed_amount,
    bill_line,
)


def pprint(claim: dict) -> None:
    for key, value in claim.items():
        print(f"{key}: {value}")
    print()


def main() -> None:
    billing = RadiologyBilling()

    print("=== Example Bills ===")
    c1 = billing.generate("XRAY", cpt="73562", icd10="M25.561",
                          side="RT", component="TC")
    pprint(c1)
    c2 = billing.generate("XRAY", cpt="71046", icd10="R05.9",
                          component="GLOBAL")
    pprint(c2)
    c3 = billing.generate("MRI", cpt="70553", icd10="R51.9",
                          component="GLOBAL")
    pprint(c3)
    c4 = billing.generate("MRI", cpt="73721", icd10="M25.562",
                          side="LT", component="26")
    pprint(c4)

    print("=== Stored Claims (one-liners) ===")
    billing.record("XRAY", "73562", "M25.561", "PATIENT_001",
                   side="RT", component="TC")
    billing.record("XRAY", "71046", "R05.9", "PATIENT_002",
                   component="GLOBAL")
    billing.record("MRI", "70553", "R51.9", "PATIENT_003",
                   component="GLOBAL")
    billing.record("MRI", "73721", "M25.562", "PATIENT_004",
                   side="LT", component="26")
    for row in billing.report:
        print(f"#{row['Claim ID']} | {row['Patient']} | {row['Modality']} | "
              f"{row['CPT']} {row['Description']} | {row['Diagnosis']} | "
              f"{row['Modifiers']} | ${row['Billed Amount']:.2f}")

    print("\n=== Formula helpers ===")
    print("Pricing formula example: base $110 at 26 -> "
          f"${calculate_billed_amount(110.00, '26'):.2f}")

    print("\n=== Validation demo ===")
    try:
        bill_line("XRAY", "99999", "R05.9")
    except CptError as exc:
        print(f"(Handled) {exc}")
    try:
        bill_line("CT", "71046", "R05.9")
    except CptError as exc:
        print(f"(Handled) {exc}")
    try:
        bill_line("XRAY", "71046", "R05.9", component="99")
    except CptError as exc:
        print(f"(Handled) {exc}")

    print("\n=== Available CPTs ===")
    for modality, table in CPT_TABLES.items():
        print(f"{modality}:")
        for record in table:
            print(f"  {record['cpt_code']} - {record['description']} "
                  f"(${record['base_price']:.2f})")


if __name__ == "__main__":
    main()