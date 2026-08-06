---
name: ops-recycling-compliance
description: "Industrial recycling compliance guidance for the Guyana (GY) jurisdiction. Use when handling recycling operations compliance tasks."
l9_schema: 1
artifact_type: documentation
tags: ['docs', 'retrieval', 'skill']
retrieval: on_demand
status: active
---
# SKILL: ops.recycling-compliance
## Version: 1.0.0
## Status: CUSTOM — built from scratch (no GitHub equivalent found in scan)
## Domain: Industrial recycling, Guyana (GY) jurisdiction

## Purpose
Validate vendor permit status, waste classification, and regulatory compliance
against Guyanese EPA rules and L9 domain pack requirements for industrial recycling.

## Input Contract
```json
{
  "vendor_id": "string",
  "vendor_name": "string",
  "permit_number": "string",
  "waste_classes": ["string"],
  "country_code": "GY",
  "extracted_fields": {}
}
```

## Output Contract
```json
{
  "compliant": true,
  "risk_score": 0.0,
  "violations": [],
  "permit_valid": true,
  "permit_expiry": "ISO8601",
  "waste_class_approved": true,
  "flags": []
}
```

## Compliance Rules (GY Jurisdiction v1)
1. Permit number must match pattern: `GY-EPA-[0-9]{6}-[A-Z]{2}`
2. Waste classes must be from approved list:
   `[ferrous_scrap, non_ferrous_scrap, electronic_waste, plastics_class_1-7,
    rubber, paper_cardboard, glass, hazardous_regulated]`
3. `hazardous_regulated` waste class → automatic risk_score += 0.4 → requires human review
4. Permit expiry < 90 days from today → flag `permit_expiring_soon`
5. Missing permit → risk_score = 1.0, compliant = false
6. Country code != GY → apply international_vendor_protocol (risk_score += 0.2)

## Fallback (native_compliance_stub)
If skill is unavailable, execute basic validation:
- Check permit_number format regex
- Flag hazardous_regulated waste class
- Set risk_score = 0.5 (conservative default)
- Set compliant = null (inconclusive — requires human review)
