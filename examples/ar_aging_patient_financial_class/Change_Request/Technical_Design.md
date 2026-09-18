# Technical Design - RCM-1610

**Change:** add `patient_financial_class` to **AR Aging Report**
**Generated:** 2026-09-18 19:21 UTC

## 1. Business Request

> Add Patient Financial Class to the AR Aging Report

**Business reason.** Needed for payer analysis to split AR aging by payer mix

## 2. Source Data

| Attribute | Value |
| --- | --- |
| Source table | rcm.dim_patient |
| Source column | patient_financial_class |
| Data type | VARCHAR(50) |
| Definition | Patient Financial Classification used to group accounts by the primary funding source (Commercial, Medicare, Medicaid, Self Pay, Workers Comp). |
| Steward | Revenue Integrity |
| Upstream producers | glue_patient_dim_load, source.patient_master |

## 3. Data Flow

```
rcm.dim_patient
   |
   v
rcm.sp_load_ar_fact
   |
   v
rcm.fact_ar
   |
   v
rcm.vw_ar_detail
   |
   v
pb_ar_aging
   |
   v
AR Aging Report
```

**Join strategy.** rcm.sp_load_ar_fact already joins rcm.dim_patient as 'p'.

## 4. Impacted Objects

| Object | Type | Impact | Layer | Risk | Rationale |
| --- | --- | --- | --- | --- | --- |
| rcm.dim_patient | table | No Change | dimension | low | Provides the attribute. rcm.sp_load_ar_fact already joins rcm.dim_patient as 'p'. |
| rcm.fact_ar | table | Modify | fact | medium | Add column patient_financial_class (existing join). |
| rcm.sp_load_ar_fact | stored_procedure | Modify | warehouse | medium | Populate rcm.fact_ar.patient_financial_class in the INSERT and SELECT lists. |
| rcm.vw_ar_detail | view | Modify | warehouse | low | Expose patient_financial_class to the reporting layer. |
| rcm.vw_ar_aging_summary | view | Review | warehouse | medium | Aggregate view: adding patient_financial_class would change the grain, so it needs a business decision rather than an automated edit. |
| df_rcm_ar | dataflow | Refresh | reporting | low | Reload the dataflow so the new column lands in the dataset. |
| pb_ar_aging | dataset | Refresh | reporting | medium | Refresh the semantic model to pick up the new column. |
| AR Aging Report | report | Modify | reporting | low | Surface the new column on the impacted visuals. |
| lambda_run_ar_load | lambda_function | Review | etl | low | lambda_run_ar_load invokes rcm.sp_load_ar_fact; confirm the orchestration still succeeds after the change. |
| lambda_refresh_powerbi_dataset | lambda_function | Review | etl | low | lambda_refresh_powerbi_dataset refreshes pb_ar_aging; confirm the orchestration still succeeds after the change. |
| sfn_rcm_nightly | step_function | Review | etl | low | sfn_rcm_nightly orchestrates lambda_run_ar_load; confirm the orchestration still succeeds after the change. |

## 5. ETL Changes

- `rcm.sp_load_ar_fact` (stored_procedure): projected p.patient_financial_class into patient_financial_class
- `rcm.vw_ar_detail` (view): selected f.patient_financial_class

### Migration

```sql
-- Forward migration: add patient_financial_class to rcm.fact_ar
-- Request: RCM-1610 - Add Patient Financial Class to the AR Aging Report
-- Generated: 2026-09-18 19:21 UTC by the RCM change automation platform
-- Review required before execution.

ALTER TABLE rcm.fact_ar
    ADD COLUMN patient_financial_class VARCHAR(50);

-- Backfill: CALL rcm.sp_load_ar_fact();  -- full snapshot reload repopulates history
```

### Diff - rcm.sp_load_ar_fact

```diff
--- a/rcm.sp_load_ar_fact.sql
+++ b/rcm.sp_load_ar_fact.sql
@@ -14,7 +14,8 @@
         denial_amount,
         balance,
         aging_bucket,
-        load_date
+        load_date,
+        patient_financial_class
     )
     SELECT
         s.ar_source_key,
@@ -32,7 +33,8 @@
             WHEN s.days_outstanding <= 90 THEN '61-90'
             ELSE '90+'
         END,
-        s.service_date
+        s.service_date,
+        p.patient_financial_class
     FROM staging.stg_ar_transactions s
     JOIN rcm.dim_patient p ON p.patient_id = s.patient_id
     JOIN rcm.dim_payer pay ON pay.payer_id = s.payer_id;
```

### Diff - rcm.vw_ar_detail

```diff
--- a/rcm.vw_ar_detail.sql
+++ b/rcm.vw_ar_detail.sql
@@ -9,7 +9,8 @@
     f.adjustment_amount,
     f.denial_amount,
     f.balance,
-    f.aging_bucket
+    f.aging_bucket,
+    f.patient_financial_class
 FROM rcm.fact_ar f
 JOIN rcm.dim_patient p ON p.patient_key = f.patient_key
 JOIN rcm.dim_payer pay ON pay.payer_key = f.payer_key;
```

## 6. Reporting Changes

| Target | Type | Action | Detail |
| --- | --- | --- | --- |
| pb_ar_aging.AR Detail | dataset_table | Add column | Add 'patient_financial_class' from rcm.vw_ar_detail to table 'AR Detail'. |
| pb_ar_aging | dataset | Refresh semantic model | Import model on schedule 'Daily 05:30 ET' must be refreshed before the column appears. |
| Total AR Balance | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| Total Charges | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| Total Payments | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| Total Adjustments | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| Total Denials | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| AR Over 90 Pct | measure | Validate | Measure sits on the modified table; confirm totals are unchanged after the refresh. |
| Aging Summary / v_summary_matrix (matrix) | visual | Review field placement | Candidate visual for surfacing 'Patient Financial Class'. |
| Aging Summary / v_balance_card (card) | visual | Review field placement | Candidate visual for surfacing 'Patient Financial Class'. |
| AR Detail / v_detail_table (table) | visual | Review field placement | Candidate visual for surfacing 'Patient Financial Class'. |
| Payer Analysis / v_payer_bar (clustered_bar) | visual | Review field placement | Candidate visual for surfacing 'Patient Financial Class'. |
| Payer Analysis / v_payer_slicer (slicer) | visual | Review field placement | Candidate visual for surfacing 'Patient Financial Class'. |
| AR Aging Report | report | Publish validation | Publish to the workspace and compare totals against the pre-change snapshot. |

### Semantic model definition

```tmdl
table 'AR Detail'
	column patient_financial_class
		dataType: string
		sourceColumn: patient_financial_class
		displayName: Patient Financial Class
		summarizeBy: none
		isHidden: false
```

## 7. Testing

- Unit tests: 8 passed, 0 failed, 0 errored of 8
- Integration tests: 14 passed, 0 failed, 0 errored of 14
- Financial reconciliation: balanced across 11 metrics

## 8. Risks

- `df_rcm_ar` must be refreshed before the report reflects the change.
- `pb_ar_aging` must be refreshed before the report reflects the change.
- rcm.vw_ar_aging_summary aggregates rows; patient_financial_class was deliberately not added to avoid changing its grain.

## 9. Rollback Strategy

- Execute `Rollback_Script.sql`, which restores the previous procedure and view definitions and drops the new column.
- Re-run the loading procedure to rebuild rcm.fact_ar with the original definition.
- Refresh the Power BI dataset so the semantic model returns to the previous schema.
