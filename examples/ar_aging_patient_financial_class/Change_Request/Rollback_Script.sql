-- Rollback: remove patient_financial_class from rcm.fact_ar
-- Request: RCM-1610 - Add Patient Financial Class to the AR Aging Report
-- Generated: 2026-09-18 19:21 UTC by the RCM change automation platform
-- Review required before execution.

-- Restore view rcm.vw_ar_detail
CREATE OR REPLACE VIEW rcm.vw_ar_detail AS
SELECT
    f.claim_id,
    p.patient_id,
    p.patient_name,
    pay.payer_name,
    f.charge_amount,
    f.payment_amount,
    f.adjustment_amount,
    f.denial_amount,
    f.balance,
    f.aging_bucket
FROM rcm.fact_ar f
JOIN rcm.dim_patient p ON p.patient_key = f.patient_key
JOIN rcm.dim_payer pay ON pay.payer_key = f.payer_key;

-- Restore stored_procedure rcm.sp_load_ar_fact
CREATE OR REPLACE PROCEDURE rcm.sp_load_ar_fact()
AS $$
BEGIN
    DELETE FROM rcm.fact_ar;

    INSERT INTO rcm.fact_ar (
        ar_key,
        claim_id,
        patient_key,
        payer_key,
        charge_amount,
        payment_amount,
        adjustment_amount,
        denial_amount,
        balance,
        aging_bucket,
        load_date
    )
    SELECT
        s.ar_source_key,
        s.claim_id,
        p.patient_key,
        pay.payer_key,
        s.charge_amount,
        s.payment_amount,
        s.adjustment_amount,
        s.denial_amount,
        s.charge_amount - s.payment_amount - s.adjustment_amount,
        CASE
            WHEN s.days_outstanding <= 30 THEN '0-30'
            WHEN s.days_outstanding <= 60 THEN '31-60'
            WHEN s.days_outstanding <= 90 THEN '61-90'
            ELSE '90+'
        END,
        s.service_date
    FROM staging.stg_ar_transactions s
    JOIN rcm.dim_patient p ON p.patient_id = s.patient_id
    JOIN rcm.dim_payer pay ON pay.payer_id = s.payer_id;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE rcm.fact_ar
    DROP COLUMN patient_financial_class;

-- CALL rcm.sp_load_ar_fact();  -- rebuild the snapshot with the original definition
