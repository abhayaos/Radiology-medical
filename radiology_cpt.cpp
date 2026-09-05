#include "radiology_cpt.h"

#include <algorithm>
#include <iomanip>
#include <sstream>

namespace radiology {

// ---------------------------------------------------------------------------
// CPT reference tables (single source mirrored from cpt.py)
// ---------------------------------------------------------------------------
static const std::vector<CptRecord> XRAY_CPT_CODES = {
    {"71045", "Chest X-Ray, Single View", "Chest", 50.00, 1, false, 0},
    {"71046", "Chest X-Ray, 2 Views", "Chest", 75.00, 2, false, 0},
    {"73562", "Knee X-Ray, 3 Views", "Knee", 110.00, 3, false, 0},
    {"73564", "Knee X-Ray, 4 or More Views", "Knee", 130.00, 4, false, 0},
    {"72100", "Lumbar Spine X-Ray, 2-3 Views", "Spine", 95.00, 2, false, 0},
};

static const std::vector<CptRecord> MRI_CPT_CODES = {
    {"70551", "MRI Brain Without Contrast", "Brain", 520.00, 1, false, 25},
    {"70553", "MRI Brain With and Without Contrast", "Brain", 780.00, 1, true, 45},
    {"73721", "MRI Knee Without Contrast", "Knee", 640.00, 1, false, 30},
    {"72148", "MRI Lumbar Spine Without Contrast", "Spine", 690.00, 1, false, 35},
    {"74183", "MRI Abdomen With and Without Contrast", "Abdomen", 860.00, 1, true, 50},
};

const std::map<std::string, std::string> ICD10_CODES = {
    {"R05.9", "Cough, unspecified"},
    {"R07.9", "Chest pain, unspecified"},
    {"M25.561", "Pain in right knee"},
    {"M25.562", "Pain in left knee"},
    {"M54.50", "Low back pain, unspecified"},
    {"R51.9", "Headache, unspecified"},
    {"R10.9", "Unspecified abdominal pain"},
};

const std::map<std::string, double> COMPONENT_MULTIPLIERS = {
    {"GLOBAL", 1.00},
    {"26", 0.40},
    {"TC", 0.60},
};

const std::vector<std::string> VALID_MODALITIES = {"XRAY", "MRI"};

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------
static std::string upper(const std::string& value) {
    std::string out = value;
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
    return out;
}

bool is_valid_side(const std::string& side) {
    return side == "RT" || side == "LT";
}

bool is_valid_component(const std::string& component) {
    return COMPONENT_MULTIPLIERS.count(component) > 0;
}

bool is_valid_icd10(const std::string& icd10) {
    return ICD10_CODES.count(icd10) > 0;
}

bool is_valid_modality(const std::string& modality) {
    const std::string key = upper(modality);
    return std::find(VALID_MODALITIES.begin(), VALID_MODALITIES.end(), key) !=
           VALID_MODALITIES.end();
}

const std::vector<CptRecord>& table_for(const std::string& modality) {
    if (upper(modality) == "XRAY") {
        return XRAY_CPT_CODES;
    }
    if (upper(modality) == "MRI") {
        return MRI_CPT_CODES;
    }
    throw CptError("Unknown modality '" + modality +
                   "'. Choose from XRAY, MRI.");
}

const CptRecord* find_cpt(const std::string& modality,
                          const std::string& cpt_code) {
    for (const CptRecord& record : table_for(modality)) {
        if (record.cpt_code == cpt_code) {
            return &record;
        }
    }
    return nullptr;
}

// ---------------------------------------------------------------------------
// Formula logic (mirrors cpt.py)
// ---------------------------------------------------------------------------
std::vector<std::string> build_modifiers(const std::string& side,
                                         const std::string& component) {
    std::vector<std::string> modifiers;
    if (is_valid_side(side)) {
        modifiers.push_back(side);
    }
    if (component == "26" || component == "TC") {
        modifiers.push_back(component);
    }
    return modifiers;
}

double calculate_billed_amount(double base, const std::string& component) {
    auto it = COMPONENT_MULTIPLIERS.find(component);
    if (it == COMPONENT_MULTIPLIERS.end()) {
        throw CptError("Invalid component '" + component +
                       "'. Choose from GLOBAL, 26, TC.");
    }
    double amount = base * it->second;
    return std::round(amount * 100.0) / 100.0;
}

CptRecord validate(const std::string& modality, const std::string& cpt_code,
                   const std::string& icd10) {
    if (!is_valid_icd10(icd10)) {
        throw CptError("Unknown ICD-10 code: " + icd10);
    }
    const CptRecord* record = find_cpt(modality, cpt_code);
    if (record == nullptr) {
        throw CptError("Unknown " + upper(modality) + " CPT code: " + cpt_code);
    }
    return *record;
}

// ---------------------------------------------------------------------------
// Claim formatting
// ---------------------------------------------------------------------------
std::string claim_summary(const Claim& claim) {
    std::ostringstream out;
    out << "#" << claim.claim_id << " | " << claim.patient_id << " | "
        << claim.modality << " | " << claim.cpt_code << " "
        << claim.description << " | " << claim.diagnosis << " | "
        << claim.modifiers << " | $" << std::fixed << std::setprecision(2)
        << claim.billed_amount;
    return out.str();
}

// ---------------------------------------------------------------------------
// Billing engine
// ---------------------------------------------------------------------------
int RadiologyBilling::record(const std::string& modality,
                             const std::string& cpt_code,
                             const std::string& icd10,
                             const std::string& patient_id,
                             const std::string& side,
                             const std::string& component) {
    CptRecord record = validate(modality, cpt_code, icd10);

    if (!is_valid_component(component)) {
        throw CptError("Invalid component '" + component +
                       "'. Choose from GLOBAL, 26, TC.");
    }

    std::vector<std::string> modifiers = build_modifiers(side, component);
    std::string modifier_str;
    for (size_t i = 0; i < modifiers.size(); ++i) {
        if (i > 0) {
            modifier_str += "-";
        }
        modifier_str += modifiers[i];
    }
    if (modifier_str.empty()) {
        modifier_str = "NONE";
    }

    Claim claim;
    claim.claim_id = static_cast<int>(claims_.size()) + 1;
    claim.patient_id = patient_id;
    claim.modality = upper(modality);
    claim.cpt_code = record.cpt_code;
    claim.description = record.description;
    claim.anatomical_site = record.anatomy;
    claim.icd10_code = icd10;
    claim.diagnosis = ICD10_CODES.at(icd10);
    claim.modifiers = modifier_str;
    claim.billed_amount = calculate_billed_amount(record.base_price,
                                                  component);

    claims_.push_back(claim);
    return claim.claim_id;
}

// ---------------------------------------------------------------------------
// Reference table text
// ---------------------------------------------------------------------------
std::string all_cpt_table_text() {
    std::ostringstream out;
    out << "XRAY:\n";
    for (const CptRecord& record : XRAY_CPT_CODES) {
        out << "  " << record.cpt_code << " - " << record.description
            << " ($" << std::fixed << std::setprecision(2)
            << record.base_price << ")\n";
    }
    out << "MRI:\n";
    for (const CptRecord& record : MRI_CPT_CODES) {
        out << "  " << record.cpt_code << " - " << record.description
            << " ($" << std::fixed << std::setprecision(2)
            << record.base_price << ")\n";
    }
    return out.str();
}

}  // namespace radiology