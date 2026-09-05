import sqlite3

# 1. Connect to SQL Database (In-Memory for demonstration)
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# 2. Schema Definition (SQL)
cursor.executescript("""
CREATE TABLE cpt_codes (
    cpt_code TEXT PRIMARY KEY,
    description TEXT,
    anatomy TEXT,
    min_views INTEGER,
    base_price REAL
);

CREATE TABLE icd10_codes (
    icd_code TEXT PRIMARY KEY,
    description TEXT
);

CREATE TABLE radiology_claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT,
    cpt_code TEXT,
    modifier TEXT,
    icd10_code TEXT,
    body_side TEXT,
    FOREIGN KEY(cpt_code) REFERENCES cpt_codes(cpt_code),
    FOREIGN KEY(icd10_code) REFERENCES icd10_codes(icd_code)
);
""")

# 3. Seed Reference Data (SQL INSERTs)
cursor.executescript("""
INSERT INTO cpt_codes VALUES 
    ('71045', 'Chest X-Ray, Single View', 'Chest', 1, 50.00),
    ('71046', 'Chest X-Ray, 2 Views', 'Chest', 2, 75.00),
    ('73562', 'Knee X-Ray, 3 Views', 'Knee', 3, 110.00),
    ('72100', 'Lumbar Spine X-Ray, 2-3 Views', 'Spine', 2, 95.00);

INSERT INTO icd10_codes VALUES 
    ('R05.9', 'Cough, unspecified'),
    ('M25.561', 'Pain in right knee'),
    ('M54.50', 'Low back pain, unspecified');
""")
conn.commit()


# 4. Helper Functions to Process Claims
def validate_and_generate_bill(cpt: str, icd10: str, side: str = None, component: str = "GLOBAL") -> dict:
    """
    Validates a radiology claim using SQL queries and calculates final reimbursement.
    
    component options: 
      - 'GLOBAL': Full procedure (no modifier)
      - '26': Professional Component (Radiologist interpretation, 40% of base)
      - 'TC': Technical Component (Facility/Equipment, 60% of base)
    """
    # SQL Query to verify CPT & ICD-10 existence
    query = """
    SELECT c.description, c.base_price, i.description 
    FROM cpt_codes c 
    CROSS JOIN icd10_codes i 
    WHERE c.cpt_code = ? AND i.icd_code = ?
    """
    cursor.execute(query, (cpt, icd10))
    result = cursor.fetchone()

    if not result:
        return {"error": "Invalid CPT or ICD-10 Code"}

    cpt_desc, base_price, icd_desc = result

    # Determine Modifiers & Price Adjustments
    modifiers = []
    if side in ["RT", "LT"]:
        modifiers.append(side)

    multiplier = 1.0
    if component == "26":
        modifiers.append("26")
        multiplier = 0.40  # 40% for Professional
    elif component == "TC":
        modifiers.append("TC")
        multiplier = 0.60  # 60% for Technical

    modifier_str = "-".join(modifiers) if modifiers else "NONE"
    final_price = round(base_price * multiplier, 2)

    return {
        "CPT": cpt,
        "CPT Description": cpt_desc,
        "ICD-10": icd10,
        "Diagnosis": icd_desc,
        "Modifiers": modifier_str,
        "Billed Amount": f"${final_price:.2f}"
    }

def record_claim(patient_id: str, cpt: str, modifier: str, icd10: str, side: str):
    """Inserts a processed claim into the SQL database."""
    cursor.execute("""
        INSERT INTO radiology_claims (patient_id, cpt_code, modifier, icd10_code, body_side)
        VALUES (?, ?, ?, ?, ?)
    """, (patient_id, cpt, modifier, icd10, side))
    conn.commit()


# 5. Example Executions

# Example 1: Right Knee X-Ray (3 views) - Technical Component Only (Facility Billing)
claim1 = validate_and_generate_bill(
    cpt="73562", 
    icd10="M25.561", 
    side="RT", 
    component="TC"
)
print("--- Claim 1 (Facility) ---")
for k, v in claim1.items():
    print(f"{k}: {v}")

record_claim("PATIENT_001", claim1["CPT"], claim1["Modifiers"], claim1["ICD-10"], "RT")

print("\n")

# Example 2: Chest X-Ray (2 views) - Global Service (Clinic owns machine & physician reads)
claim2 = validate_and_generate_bill(
    cpt="71046", 
    icd10="R05.9", 
    component="GLOBAL"
)
print("--- Claim 2 (Global) ---")
for k, v in claim2.items():
    print(f"{k}: {v}")

record_claim("PATIENT_002", claim2["CPT"], claim2["Modifiers"], claim2["ICD-10"], "N/A")


# 6. Retrieve Claims with SQL JOIN Query
print("\n--- All Claims Stored in Database (SQL JOIN) ---")
sql_report = """
SELECT 
    rc.claim_id,
    rc.patient_id,
    rc.cpt_code,
    c.description AS cpt_desc,
    rc.modifier,
    rc.icd10_code,
    i.description AS diagnosis
FROM radiology_claims rc
JOIN cpt_codes c ON rc.cpt_code = c.cpt_code
JOIN icd10_codes i ON rc.icd10_code = i.icd_code
"""

for row in cursor.execute(sql_report):
    print(row)

# Clean up
conn.close()
