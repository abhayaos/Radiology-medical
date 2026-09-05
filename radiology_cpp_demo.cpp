// Demo CLI for the C++ radiology billing engine (radiology_cpt.{h,cpp}).
#include "radiology_cpt.h"

#include <exception>
#include <iostream>

using radiology::CptError;
using radiology::RadiologyBilling;

int main() {
    RadiologyBilling billing;

    std::cout << "=== Stored Claims ===" << std::endl;
    billing.record("XRAY", "73562", "M25.561", "PATIENT_001", "RT", "TC");
    billing.record("XRAY", "71046", "R05.9", "PATIENT_002", "", "GLOBAL");
    billing.record("MRI", "70553", "R51.9", "PATIENT_003", "", "GLOBAL");
    billing.record("MRI", "73721", "M25.562", "PATIENT_004", "LT", "26");

    for (const auto& claim : billing.report()) {
        std::cout << radiology::claim_summary(claim) << std::endl;
    }

    std::cout << "\n=== Validation demo ===" << std::endl;
    try {
        billing.record("XRAY", "99999", "R05.9", "BAD_001");
    } catch (const CptError& exc) {
        std::cout << "(Handled) " << exc.what() << std::endl;
    }
    try {
        billing.record("CT", "71046", "R05.9", "BAD_002");
    } catch (const CptError& exc) {
        std::cout << "(Handled) " << exc.what() << std::endl;
    }
    try {
        billing.record("XRAY", "71046", "R05.9", "BAD_003", "", "99");
    } catch (const CptError& exc) {
        std::cout << "(Handled) " << exc.what() << std::endl;
    }

    std::cout << "\n=== Formula helpers ===" << std::endl;
    std::cout << "Pricing formula example: base $110 at 26 -> $"
              << radiology::calculate_billed_amount(110.00, "26") << std::endl;

    std::cout << "\n=== Available CPTs ===" << std::endl;
    std::cout << radiology::all_cpt_table_text();

    return 0;
}