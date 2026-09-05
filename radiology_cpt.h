#pragma once

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace radiology {

// ---------------------------------------------------------------------------
// CPT reference data
// ---------------------------------------------------------------------------
struct CptRecord {
    std::string cpt_code;
    std::string description;
    std::string anatomy;
    double base_price;
    int min_views;
    bool with_contrast;
    int duration_min;
};

// Shared ICD-10 diagnosis reference
extern const std::map<std::string, std::string> ICD10_CODES;

// Pricing rules
extern const std::map<std::string, double> COMPONENT_MULTIPLIERS;
extern const std::vector<std::string> VALID_MODALITIES;

// ---------------------------------------------------------------------------
// Exceptions
// ---------------------------------------------------------------------------
class CptError : public std::invalid_argument {
public:
    explicit CptError(const std::string& message)
        : std::invalid_argument(message) {}
};

// ---------------------------------------------------------------------------
// Core logic
// ---------------------------------------------------------------------------
bool is_valid_side(const std::string& side);
bool is_valid_component(const std::string& component);
bool is_valid_icd10(const std::string& icd10);
bool is_valid_modality(const std::string& modality);

const CptRecord* find_cpt(const std::string& modality,
                          const std::string& cpt_code);

// Collects the modifier list (RT/LT and/or 26/TC)
std::vector<std::string> build_modifiers(const std::string& side,
                                         const std::string& component);

// Applies the component multiplier formula to the base price
double calculate_billed_amount(double base, const std::string& component);

// Full validation pipeline; throws CptError on any invalid input
CptRecord validate(const std::string& modality, const std::string& cpt_code,
                   const std::string& icd10);

// ---------------------------------------------------------------------------
// Claim model
// ---------------------------------------------------------------------------
struct Claim {
    int claim_id = 0;
    std::string patient_id;
    std::string modality;
    std::string cpt_code;
    std::string description;
    std::string anatomical_site;
    std::string icd10_code;
    std::string diagnosis;
    std::string modifiers;
    double billed_amount = 0.0;
};

std::string claim_summary(const Claim& claim);

// ---------------------------------------------------------------------------
// Billing engine
// ---------------------------------------------------------------------------
class RadiologyBilling {
public:
    // Validate and store a claim, returning its sequence ID.
    int record(const std::string& modality, const std::string& cpt_code,
               const std::string& icd10, const std::string& patient_id,
               const std::string& side = "", const std::string& component = "GLOBAL");

    // Returns details of all recorded claims.
    const std::vector<Claim>& report() const { return claims_; }
    size_t claim_count() const { return claims_.size(); }

private:
    std::vector<Claim> claims_;
};

// ---------------------------------------------------------------------------
// Print helpers
// ---------------------------------------------------------------------------
std::string all_cpt_table_text();

}  // namespace radiology