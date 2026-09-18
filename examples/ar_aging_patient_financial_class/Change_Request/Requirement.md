# Requirement RCM-1610

_Generated 2026-09-18 19:21 UTC by the RCM change automation platform._

## Business Request

> Add Patient Financial Class to the AR Aging Report

## Structured Requirement

```json
{
  "report": "AR Aging Report",
  "requested_column": "Patient Financial Class",
  "business_reason": "Needed for payer analysis to split AR aging by payer mix"
}
```

| Attribute | Value |
| --- | --- |
| Request ID | RCM-1610 |
| Requested by | business_user |
| Change type | add_column |
| Parser | rule_based |
| Match confidence | 1.00 |

## Resolved Source

| Attribute | Value |
| --- | --- |
| Business term | Patient Financial Class |
| Source table | rcm.dim_patient |
| Source column | patient_financial_class |
| Data type | VARCHAR(50) |
| Nullable | False |
| Certified | True |
| Steward | Revenue Integrity |
| Domain values | Commercial, Medicare, Medicaid, Self Pay, Workers Comp |

**Definition.** Patient Financial Classification used to group accounts by the primary funding source (Commercial, Medicare, Medicaid, Self Pay, Workers Comp).

## Metadata Evidence

| Source | Reference | Detail |
| --- | --- | --- |
| Data Dictionary | Patient Financial Class | fuzzy match score 1.00 for 'Patient Financial Class' |
| Information Schema | rcm.dim_patient.patient_financial_class | VARCHAR(50), nullable=False |
| Column Lineage Repository | rcm.dim_patient | upstream producers: glue_patient_dim_load, source.patient_master |
| Jira | RCM-1187, RCM-1402, RCM-1544, RCM-1610 | history for rcm.dim_patient and AR Aging Report |
| Existing Documentation | docs/reports/ar_aging_report.md, docs/standards/warehouse_standards.md, docs/standards/power_bi_runbook.md | documents referencing rcm.dim_patient or AR Aging Report |

## Related Jira History

- RCM-1187: Load patient financial class into the patient dimension (Done)
- RCM-1402: AR Aging Report balance reconciliation variance after aging bucket change (Done)
- RCM-1544: Add payer analysis page to AR Aging Report (Done)
- RCM-1610: Business request: financial class breakdown for payer analysis (In Progress)
