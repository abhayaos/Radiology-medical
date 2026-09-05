"""cpt.py - central formulas and logic for radiology billing.

Holds all CPT reference data (X-Ray + MRI), ICD-10 diagnoses, the component
modifier rules, and the billing calculation engine used across the project.

Components:
    GLOBAL - full procedure, no modifier            -> 100% of base price
    26     - professional (radiologist) component   ->  40% of base price
    TC     - technical (equipment/facility) component -> 60% of base price

Body-side modifiers (RT / LT) are appended automatically when supplied and
do not change the price.
"""

# ---------------------------------------------------------------------------
# CPT reference data
# ---------------------------------------------------------------------------
XRAY_CPT_CODES = [
    {"cpt_code": "71045", "description": "Chest X-Ray, Single View",
     "anatomy": "Chest", "min_views": 1, "base_price": 50.00},
    {"cpt_code": "71046", "description": "Chest X-Ray, 2 Views",
     "anatomy": "Chest", "min_views": 2, "base_price": 75.00},
    {"cpt_code": "73562", "description": "Knee X-Ray, 3 Views",
     "anatomy": "Knee", "min_views": 3, "base_price": 110.00},
    {"cpt_code": "73564", "description": "Knee X-Ray, 4 or More Views",
     "anatomy": "Knee", "min_views": 4, "base_price": 130.00},
    {"cpt_code": "72100", "description": "Lumbar Spine X-Ray, 2-3 Views",
     "anatomy": "Spine", "min_views": 2, "base_price": 95.00},
]

MRI_CPT_CODES = [
    {"cpt_code": "70551", "description": "MRI Brain Without Contrast",
     "anatomy": "Brain", "with_contrast": False,
     "duration_min": 25, "base_price": 520.00},
    {"cpt_code": "70553", "description": "MRI Brain With and Without Contrast",
     "anatomy": "Brain", "with_contrast": True,
     "duration_min": 45, "base_price": 780.00},
    {"cpt_code": "73721", "description": "MRI Knee Without Contrast",
     "anatomy": "Knee", "with_contrast": False,
     "duration_min": 30, "base_price": 640.00},
    {"cpt_code": "72148", "description": "MRI Lumbar Spine Without Contrast",
     "anatomy": "Spine", "with_contrast": False,
     "duration_min": 35, "base_price": 690.00},
    {"cpt_code": "74183", "description": "MRI Abdomen With and Without Contrast",
     "anatomy": "Abdomen", "with_contrast": True,
     "duration_min": 50, "base_price": 860.00},
]

CPT_TABLES = {
    "XRAY": XRAY_CPT_CODES,
    "MRI": MRI_CPT_CODES,
}

# ---------------------------------------------------------------------------
# ICD-10 diagnosis reference (shared across modalities)
# ---------------------------------------------------------------------------
ICD10_CODES = {
    "R05.9": "Cough, unspecified",
    "R07.9": "Chest pain, unspecified",
    "M25.561": "Pain in right knee",
    "M25.562": "Pain in left knee",
    "M54.50": "Low back pain, unspecified",
    "R51.9": "Headache, unspecified",
    "R10.9": "Unspecified abdominal pain",
}

# ---------------------------------------------------------------------------
# Pricing formulas and rules
# ---------------------------------------------------------------------------
COMPONENT_MULTIPLIERS = {"GLOBAL": 1.00, "26": 0.40, "TC": 0.60}
VALID_SIDES = {"RT", "LT"}
VALID_MODALITIES = tuple(CPT_TABLES)


class CptError(ValueError):
    """Raised when a radiology claim cannot be validated."""


def get_cpt(modality: str, cpt_code: str) -> dict | None:
    """Return a copy of the CPT record for `cpt_code`, or None."""
    table = _table_for(modality)
    for record in table:
        if record["cpt_code"] == cpt_code:
            return dict(record)
    return None


def _table_for(modality: str) -> list:
    key = modality.upper()
    if key not in CPT_TABLES:
        raise CptError(
            f"Unknown modality '{modality}'. Choose from "
            f"{', '.join(VALID_MODALITIES)}."
        )
    return CPT_TABLES[key]


def build_modifiers(side: str = None, component: str = "GLOBAL") -> list:
    """Build the modifier list for a claim.

    - GLOBAL adds no component modifier.
    - 26 / TC add the component modifier.
    - RT / LT add a body-side modifier when supplied.
    """
    modifiers = []
    if side in VALID_SIDES:
        modifiers.append(side)
    if component in ("26", "TC"):
        modifiers.append(component)
    return modifiers


def calculate_billed_amount(base_price: float,
                            component: str = "GLOBAL") -> float:
    """Apply the component multiplier formula to a base price."""
    if component not in COMPONENT_MULTIPLIERS:
        raise CptError(
            f"Invalid component '{component}'. Choose from "
            f"{', '.join(COMPONENT_MULTIPLIERS)}."
        )
    return round(base_price * COMPONENT_MULTIPLIERS[component], 2)


def validate_and_generate_bill(modality: str, cpt: str, icd10: str,
                               side: str = None,
                               component: str = "GLOBAL") -> dict:
    """Validate a claim and return the full billed breakdown (logic core).

    Raises CptError for an unknown modality, CPT code, ICD-10 code, or
    component.
    """
    if icd10 not in ICD10_CODES:
        raise CptError(f"Unknown ICD-10 code: {icd10}")
    if component not in COMPONENT_MULTIPLIERS:
        raise CptError(
            f"Invalid component '{component}'. Choose from "
            f"{', '.join(COMPONENT_MULTIPLIERS)}."
        )

    record = get_cpt(modality, cpt)
    if record is None:
        raise CptError(f"Unknown {modality.upper()} CPT code: {cpt}")

    modifiers = build_modifiers(side, component)
    modifier_str = "-".join(modifiers) if modifiers else "NONE"
    final_price = calculate_billed_amount(record["base_price"], component)

    claim = {
        "Modality": modality.upper(),
        "CPT": cpt,
        "Description": record["description"],
        "Anatomy": record["anatomy"],
        "ICD-10": icd10,
        "Diagnosis": ICD10_CODES[icd10],
        "Modifiers": modifier_str,
        "Billed Amount": final_price,
    }

    if modality.upper() == "MRI":
        claim.update({
            "With Contrast": record["with_contrast"],
            "Est. Duration (min)": record["duration_min"],
        })
    else:
        claim["Min Views"] = record["min_views"]

    return claim


def bill_line(modality: str, cpt: str, icd10: str, side: str = None,
              component: str = "GLOBAL") -> str:
    """Render a one-line summary of a validated claim."""
    claim = validate_and_generate_bill(modality, cpt, icd10, side, component)
    return (
        f"{claim['CPT']} {claim['Description']} | {claim['Diagnosis']} | "
        f"{claim['Modifiers']} | ${claim['Billed Amount']:.2f}"
    )


# ---------------------------------------------------------------------------
# Claim engine (stores claims with an in-memory database)
# ---------------------------------------------------------------------------
class RadiologyBilling:
    """Validates, stores, and reports radiology claims."""

    def __init__(self):
        self._last_claim = None
        self._claims = []
        self._report = []

    @property
    def claims(self) -> list:
        return list(self._claims)

    @property
    def report(self) -> list:
        return list(self._report)

    def generate(self, modality: str, cpt: str, icd10: str,
                 side: str = None, component: str = "GLOBAL") -> dict:
        """Build and validate a bill (does not store the claim)."""
        return validate_and_generate_bill(
            modality, cpt, icd10, side, component)

    def record(self, modality: str, cpt: str, icd10: str,
               patient_id: str, side: str = None,
               component: str = "GLOBAL") -> int:
        """Validate, store, and report a claim. Returns claim sequence ID."""
        claim = validate_and_generate_bill(modality, cpt, icd10, side,
                                           component)
        claim_id = len(self._claims) + 1
        self._claims.append(claim)
        self._report.append({
            "Claim ID": claim_id,
            "Patient": patient_id,
            "Modality": claim["Modality"],
            "CPT": claim["CPT"],
            "Description": claim["Description"],
            "ICD-10": claim["ICD-10"],
            "Diagnosis": claim["Diagnosis"],
            "Modifiers": claim["Modifiers"],
            "Billed Amount": claim["Billed Amount"],
        })
        self._last_claim = claim
        return claim_id