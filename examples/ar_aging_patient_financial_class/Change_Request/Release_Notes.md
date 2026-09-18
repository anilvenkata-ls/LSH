# Release Notes - 2026.09 AR Enhancements

**Date:** 2026-09-18 19:21 UTC
**Request:** RCM-1610 - Add Patient Financial Class to the AR Aging Report

## What changed

- `patient_financial_class` (VARCHAR(50)) is now available on **AR Aging Report**.
- Sourced from `rcm.dim_patient` and denormalised onto `rcm.fact_ar`.

## Deployment steps

- Run `Generated_SQL.sql` in the target environment.
- Re-run the loading procedure for `rcm.fact_ar` (a full snapshot reload backfills history).
- Refresh the Power BI dataset `pb_ar_aging`.
- Publish the updated report and validate the new field on the impacted visuals.

## Validation performed

- Unit tests: 8 passed, 0 failed, 0 errored of 8
- Integration tests: 14 passed, 0 failed, 0 errored of 14
- Financial reconciliation: balanced across 11 metrics

## Known impacts

- `df_rcm_ar` must be refreshed before the report reflects the change.
- `pb_ar_aging` must be refreshed before the report reflects the change.
- rcm.vw_ar_aging_summary aggregates rows; patient_financial_class was deliberately not added to avoid changing its grain.
