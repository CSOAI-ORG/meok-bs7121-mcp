"""Smoke tests for meok-bs7121-mcp."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    lookup_bs7121_clause, classify_lift_category, triage_cpa_hire_vs_contract_lift,
    check_ap_competence, validate_lift_plan, calculate_ground_bearing_pressure,
    check_exclusion_zone, schedule_loler_thorough_exam, check_cpcs_card,
    check_cap1096_aviation, BS_7121_PARTS, CPCS_CATEGORIES,
)


def _call(t, **kw):
    fn = t.fn if hasattr(t, "fn") else t
    return fn(**kw)


def test_clause_lookup_returns_paraphrase():
    r = _call(lookup_bs7121_clause, part="1", section="4.1")
    assert "competent person" in r["intent_paraphrase"].lower()
    assert r["title"] == "BS 7121-1:2016"


def test_classify_critical_for_personnel_lift():
    r = _call(classify_lift_category, load_weight_t=2, swl_t=10, radius_m=15,
              is_personnel_lift=True)
    assert r["category"] == "critical"
    assert r["ap_signoff_required"] is True


def test_classify_complex_for_high_utilisation():
    r = _call(classify_lift_category, load_weight_t=9.5, swl_t=10, radius_m=15)
    assert r["category"] == "complex"


def test_classify_basic_for_routine():
    r = _call(classify_lift_category, load_weight_t=2, swl_t=10, radius_m=15)
    assert r["category"] == "basic"


def test_cpa_contract_lift_when_full_supply():
    r = _call(triage_cpa_hire_vs_contract_lift,
              crane_supplied_with_operator=True,
              site_supplied_ap=False,
              site_supplied_slinger=False,
              customer_directing_lift=False,
              job_value_gbp=8000)
    assert r["contract_type"] == "CPA Contract Lift"


def test_cpa_hire_when_customer_runs_show():
    r = _call(triage_cpa_hire_vs_contract_lift,
              crane_supplied_with_operator=True,
              site_supplied_ap=True,
              site_supplied_slinger=True,
              customer_directing_lift=True,
              job_value_gbp=8000)
    assert r["contract_type"] == "CPA Hire"
    assert "Baldwins" in r["potential_dispute_exposure"]


def test_ap_expired_card_flagged():
    r = _call(check_ap_competence, name="A", a88_cpcs_card_number="X1",
              a88_card_expiry="2020-01-01",
              qualifications=["Appointed Person Course CPCS A88"],
              years_experience=5)
    assert any("EXPIRED" in i for i in r["issues"])


def test_ap_valid_competent_for_standard():
    from datetime import date, timedelta
    exp = (date.today() + timedelta(days=400)).isoformat()
    r = _call(check_ap_competence, name="B", a88_cpcs_card_number="X2",
              a88_card_expiry=exp,
              qualifications=["Appointed Person CPCS A88", "Slinger A40"],
              years_experience=8)
    assert "standard" in r["competent_for"]


def test_lift_plan_all_pass_grade_a():
    r = _call(validate_lift_plan, has_load_weight=True, has_swl_check=True,
              has_ground_assessment=True, has_exclusion_zone=True,
              has_method_statement=True, has_emergency_procedure=True,
              has_ap_signoff=True, has_toolbox_talk_record=True,
              has_weather_cutoff=True, has_communications_plan=True)
    assert r["grade"] == "A"


def test_lift_plan_missing_method_statement_fail():
    r = _call(validate_lift_plan, has_load_weight=True, has_swl_check=True)
    assert r["grade"] in ("F", "C")


def test_gbp_exceeds_soil():
    r = _call(calculate_ground_bearing_pressure,
              crane_mass_kg=50000, counterweight_mass_kg=30000,
              load_mass_kg=20000, radius_m=25,
              outrigger_pad_area_m2=1.0, soil_safe_bearing_kpa=100)
    assert "EXCEED" in r["verdict"] or "CRITICAL" in r["verdict"]


def test_gbp_within_bearing():
    r = _call(calculate_ground_bearing_pressure,
              crane_mass_kg=10000, counterweight_mass_kg=5000,
              load_mass_kg=2000, radius_m=10,
              outrigger_pad_area_m2=2.0, soil_safe_bearing_kpa=200)
    assert "Within" in r["verdict"]


def test_exclusion_zone_returns_radius_and_barrier():
    r = _call(check_exclusion_zone, radius_m=15, load_height_m=20)
    assert r["minimum_radius_m"] > 0
    assert r["barrier_required"] is True


def test_loler_sling_is_6_month():
    r = _call(schedule_loler_thorough_exam,
              equipment_type="sling", equipment_id="SL-001",
              last_te_date="2026-01-01")
    assert r["interval_months"] == 6


def test_loler_personnel_lift_is_6_month():
    r = _call(schedule_loler_thorough_exam,
              equipment_type="mobile_crane", equipment_id="MC-1",
              last_te_date="2026-01-01", used_for_personnel=True)
    assert r["interval_months"] == 6


def test_loler_overdue_flagged():
    r = _call(schedule_loler_thorough_exam,
              equipment_type="mobile_crane", equipment_id="MC-2",
              last_te_date="2024-01-01")
    assert r["overdue"] is True


def test_cpcs_a40_valid():
    from datetime import date, timedelta
    exp = (date.today() + timedelta(days=400)).isoformat()
    r = _call(check_cpcs_card, card_number="CP-12345",
              card_category="A40", expiry_date=exp)
    assert r["valid"] is True
    assert "Mobile crane" in r["category_label"]


def test_cpcs_expired_flagged():
    r = _call(check_cpcs_card, card_number="CP-OLD",
              card_category="A36", expiry_date="2020-01-01")
    assert r["valid"] is False


def test_cap1096_tall_crane_near_aerodrome():
    r = _call(check_cap1096_aviation,
              crane_height_agl_m=30, within_6km_of_aerodrome=True)
    assert r["notification_required"] is True


def test_cap1096_short_far_from_aerodrome():
    r = _call(check_cap1096_aviation,
              crane_height_agl_m=12, within_6km_of_aerodrome=False)
    assert r["notification_required"] is False


def test_bs_parts_table_has_5():
    assert len(BS_7121_PARTS) >= 5


def test_attestation_signed():
    r = _call(lookup_bs7121_clause, part="3", section="4")
    assert r["issuer"] == "meok-bs7121-mcp"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
