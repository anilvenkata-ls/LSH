# Power BI Change Plan - AR Aging Report

**Dataset:** pb_ar_aging  
**Workspace:** RCM Analytics  
**Refresh required:** yes

## Actions

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

## Impacted measures

- Total AR Balance
- Total Charges
- Total Payments
- Total Adjustments
- Total Denials
- AR Over 90 Pct

## Impacted relationships

- AR Detail[aging_bucket] -> AR Aging Summary[aging_bucket]

## Impacted visuals

- Aging Summary / v_summary_matrix (matrix)
- Aging Summary / v_balance_card (card)
- AR Detail / v_detail_table (table)
- Payer Analysis / v_payer_bar (clustered_bar)
- Payer Analysis / v_payer_slicer (slicer)

## Semantic model definition (TMDL)

```tmdl
table 'AR Detail'
	column patient_financial_class
		dataType: string
		sourceColumn: patient_financial_class
		displayName: Patient Financial Class
		summarizeBy: none
		isHidden: false
```
