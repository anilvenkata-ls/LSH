# Example output

`ar_aging_patient_financial_class/Change_Request/` is a committed snapshot of a real run, so the
deliverables can be reviewed without installing anything. It was produced by:

```bash
rcm-change run "Add Patient Financial Class to the AR Aging Report" \
  --reason "Needed for payer analysis to split AR aging by payer mix" \
  --request-id RCM-1610 \
  --release "2026.09 AR Enhancements" \
  -o examples/ar_aging_patient_financial_class
```

Worth reading first:

- `Technical_Design.md` — the impact matrix, the generated diffs and the rollback strategy.
- `Validation_Report.md` — the before/after reconciliation table and every executed test.
- `Generated_SQL.sql` and `Rollback_Script.sql` — the forward and reverse changes.

Regenerating the snapshot changes only the embedded timestamps, since the pipeline is
deterministic when no LLM provider is configured.
