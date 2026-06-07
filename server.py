#!/usr/bin/env python3
"""
MEOK BS 7121 Lift-Plan Compliance MCP
=========================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-bs7121-mcp -->

WHAT THIS DOES
--------------
BS 7121 ("Code of Practice for the Safe Use of Cranes") is the UK lift-planning
bible. Five active parts most operators have to reference daily:

  Part 1:2016  General (the umbrella code)
  Part 3:2017  Mobile cranes
  Part 4:2010  Lorry loaders (hiab)
  Part 5:2019  Tower cranes
  Part 7:2020  Overhead travelling and underhung cranes

Plus the regulatory layer:
  LOLER 1998 — Lifting Operations and Lifting Equipment Regs (Reg 9 = TE/PSI)
  PUWER 1998 — Provision and Use of Work Equipment
  CDM 2015  — Principal Contractor named for lifting ops
  CPCS A02 (crawler), A40 (mobile), A60 (tower), A66 (telescopic crawler) cards

This MCP is the callable compliance layer that sits ABOVE 3D Lift Plan and
Lolerflow — it doesn't simulate; it validates, classifies, and produces
audit-quality compliance attestations.

REAL UK CASES THAT MOTIVATE THIS MCP
-------------------------------------
- Brand Energy & Infrastructure Services UK — £1.6m HSE fine (Nov 2024),
  Jack Phillips (24) killed Eastbourne. Expired sling + missing exclusion zone.
- Baldwins Crane Hire v Vision Modular Systems (ongoing 2026, £951k claim) —
  CPA Condition 9(d) negligence / misdirection / misuse — proves Contract-Lift
  vs Hire triage at the QUOTE stage is the £100k+ wedge.

TOOLS (10)
----------
- lookup_bs7121_clause(part, section)         → relevant clause text + intent
- classify_lift_category(weight, geom, env)   → basic/standard/complex/critical
- triage_cpa_hire_vs_contract_lift(job)       → liability split + £ exposure
- check_ap_competence(person)                 → Appointed Person verification
- validate_lift_plan(plan_dict)               → BS 7121 compliance scoring
- calculate_ground_bearing_pressure(spec)     → GBP + outrigger pad sizing
- check_exclusion_zone(crane, load, site)     → zone radius + barrier reqs
- schedule_loler_thorough_exam(equipment)     → 6/12-month cadence
- check_cpcs_card(card_number, category)      → operator credential check
- check_cap1096_aviation(crane_height, lat_lon) → CAA Section 50 notification

WHY YOU PAY
-----------
Pro tier £299/mo justified by:
  - Baldwins-style avoided £951k counter-claim
  - Brand Energy-style avoided £1.6m HSE fine
  - Insurer + Principal Contractor preference for documented lift plans

PRICING
-------
Free MIT self-host · £99/mo Starter · £299/mo Pro · £799/mo Enterprise.

REGULATORY BASIS
----------------
BS 7121-1:2016, -3:2017, -4:2010, -5:2019, -7:2020
LOLER 1998 (SI 1998/2307)
PUWER 1998 (SI 1998/2306)
CDM 2015 (SI 2015/51)
CAA Civil Aviation Act 1982 §50, CAP 1096
CPA Model Conditions of Hire 2011 + 2021 amendments
"""

from __future__ import annotations
import hashlib, hmac, json, math, os
from datetime import datetime, timezone, date
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("meok-bs7121")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables
# ──────────────────────────────────────────────────────────────────────

BS_7121_PARTS = {
    "1": ("BS 7121-1:2016", "General — code of practice for the safe use of cranes"),
    "3": ("BS 7121-3:2017", "Mobile cranes"),
    "4": ("BS 7121-4:2010", "Lorry loaders"),
    "5": ("BS 7121-5:2019", "Tower cranes"),
    "7": ("BS 7121-7:2020", "Overhead travelling and underhung cranes"),
}

# Key sections most-referenced day-to-day (paraphrased intent, not the BSI text)
BS_7121_KEY_CLAUSES = {
    ("1", "4.1"): "Lifting operation MUST be planned by a competent person (AP).",
    ("1", "4.2"): "Planning shall include selection of crane, accessories, ground conditions, route, environmental conditions.",
    ("1", "4.3"): "A Method Statement must be produced for every standard, complex, or critical lift.",
    ("1", "5.4"): "Persons involved in lifting operations shall be competent.",
    ("1", "5.5"): "Competence demonstrated via training records, CPCS/NPORS cards, and continued assessment.",
    ("1", "6.2"): "Pre-use inspection of crane + accessories.",
    ("1", "8"): "Lifting operations near overhead lines — minimum exclusion distances per energy.",
    ("3", "4"): "Mobile-crane-specific planning — duty chart selection, outriggers, ground pressure.",
    ("4", "5"): "Lorry-loader-specific — stability before slewing, load on the truck deck check.",
    ("5", "6"): "Tower-crane-specific — climbing, anchoring, derrick stress, slewing radius.",
    ("5", "9"): "Two or more cranes (multi-crane / tandem) — additional planning + AP signoff per crane.",
}

# CPCS operator card categories
CPCS_CATEGORIES = {
    "A02": "Crawler crane",
    "A40": "Mobile crane (slew + telescopic)",
    "A60": "Tower crane",
    "A66": "Telescopic handler / crawler crane (telescopic)",
    "A73": "Slinger/signaller",
    "A36": "Lorry loader (hiab)",
    "A77": "Crawler crane (lattice)",
    "A85": "Crane supervisor (CCS)",
    "A88": "Appointed Person (AP)",
}

# Lift category thresholds (from BS 7121-1)
LIFT_CATEGORY_RULES = [
    ("critical", "Out of duty-chart envelope OR personnel lift OR tandem lift OR over occupied area"),
    ("complex",  "Multi-crane or load close to envelope limit OR over road OR specialist rigging"),
    ("standard", "Within duty chart, single crane, standard rigging, dedicated exclusion zone"),
    ("basic",    "Routine lift, well within duty chart, low risk"),
]

# CAP 1096 / Civil Aviation Act §50 — when crane near aerodrome needs notification
CAA_SECTION_50_THRESHOLD_M = 10.0


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(),
                    json.dumps(payload, sort_keys=True, default=str).encode(),
                    hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {**payload, "ts": _ts(), "sig": _sign(payload),
            "issuer": "meok-bs7121-mcp", "version": "1.0.0"}


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def lookup_bs7121_clause(part: str, section: str) -> dict:
    """Look up a BS 7121 clause across parts 1/3/4/5/7.

    Args:
      part: '1' / '3' / '4' / '5' / '7'
      section: e.g. '4.1', '5.4'
    """
    title, label = BS_7121_PARTS.get(part, ("", "Unknown part"))
    intent = BS_7121_KEY_CLAUSES.get((part, section), "")
    return _attestation({
        "tool": "lookup_bs7121_clause",
        "part": part,
        "section": section,
        "title": title,
        "label": label,
        "intent_paraphrase": intent or "Clause not in shipped index — consult BSI for full text.",
        "advisory": (
            "Refer to full BSI standard for legal compliance. This is a paraphrased intent only."
        ),
    })


@mcp.tool()
def classify_lift_category(
    load_weight_t: float,
    swl_t: float,
    radius_m: float,
    is_personnel_lift: bool = False,
    is_tandem_lift: bool = False,
    is_over_occupied: bool = False,
    is_over_public_road: bool = False,
    crane_envelope_ok: bool = True,
) -> dict:
    """Classify a lift as basic / standard / complex / critical per BS 7121-1.

    Args:
      load_weight_t: load weight in tonnes
      swl_t: Safe Working Load at the radius
      radius_m: working radius in metres
    """
    util_pct = (load_weight_t / max(0.01, swl_t)) * 100.0

    category = "basic"
    reasons = []
    if is_personnel_lift:
        category = "critical"; reasons.append("personnel lift")
    if is_tandem_lift:
        category = "critical"; reasons.append("tandem (multi-crane) lift")
    if is_over_occupied:
        category = "critical"; reasons.append("load over occupied area")
    if not crane_envelope_ok:
        category = "critical"; reasons.append("outside duty-chart envelope")
    if category != "critical":
        if util_pct > 90 or is_over_public_road:
            category = "complex"
            reasons.append(f"utilisation {util_pct:.0f}% > 90% or over public road")
        elif util_pct > 70:
            category = "standard"
            reasons.append(f"utilisation {util_pct:.0f}% > 70%")

    return _attestation({
        "tool": "classify_lift_category",
        "load_weight_t": load_weight_t,
        "swl_t": swl_t,
        "radius_m": radius_m,
        "utilisation_pct": round(util_pct, 1),
        "category": category,
        "reasons": reasons,
        "ap_signoff_required": category in ("complex", "critical"),
        "method_statement_required": category in ("standard", "complex", "critical"),
        "second_ap_required": category == "critical" and is_tandem_lift,
    })


@mcp.tool()
def triage_cpa_hire_vs_contract_lift(
    crane_supplied_with_operator: bool = True,
    site_supplied_ap: bool = False,
    site_supplied_slinger: bool = False,
    customer_directing_lift: bool = True,
    job_value_gbp: float = 0.0,
) -> dict:
    """Triage whether a job is CPA Hire or CPA Contract Lift — the legal
    liability shift documented in Baldwins v Vision (£951k) cases.

    Returns the recommended contract type + the £ liability exposure flag.
    """
    is_contract_lift = (
        crane_supplied_with_operator and
        not site_supplied_ap and
        not site_supplied_slinger and
        not customer_directing_lift
    )

    if is_contract_lift:
        contract_type = "CPA Contract Lift"
        liability = "Crane hirer carries full lifting-op liability (insured by hirer)."
        price_uplift_pct = "15-30% on hire-only rate"
        recommended_action = (
            "Quote Contract Lift price. AP + lift plan + slinger by hirer. "
            "Insurance burden on hirer. Higher margin."
        )
    else:
        contract_type = "CPA Hire"
        liability = "Customer carries lifting-op liability. Crane hirer supplies crane + operator only."
        price_uplift_pct = "n/a — hire rate"
        recommended_action = (
            "Quote Hire rate. Customer responsible for AP + lift plan + slinger. "
            "Document this in quote per CPA Conditions to defend against Condition 9(d) "
            "negligence/misdirection/misuse claims."
        )

    return _attestation({
        "tool": "triage_cpa_hire_vs_contract_lift",
        "contract_type": contract_type,
        "liability_position": liability,
        "price_uplift_typical": price_uplift_pct,
        "recommended_action": recommended_action,
        "job_value_gbp": job_value_gbp,
        "potential_dispute_exposure": "Up to job value × 5x in counter-claim (Baldwins v Vision precedent).",
        "evidence_to_save": [
            "Signed quote stating contract type",
            "Customer's named AP (if Hire-only)",
            "Method statement source (whose responsibility)",
            "Pre-lift toolbox-talk attendance",
        ],
    })


@mcp.tool()
def check_ap_competence(
    name: str,
    a88_cpcs_card_number: str = "",
    a88_card_expiry: str = "",
    qualifications: Optional[list] = None,
    years_experience: int = 0,
) -> dict:
    """Verify an Appointed Person's competence per BS 7121-1 §5.4-5.5."""
    qualifications = qualifications or []
    today = date.today()
    issues = []

    try:
        exp = date.fromisoformat(a88_card_expiry)
        days_to_expiry = (exp - today).days
        if days_to_expiry < 0:
            issues.append("A88 CPCS card EXPIRED")
        elif days_to_expiry < 30:
            issues.append(f"A88 CPCS card expires in {days_to_expiry} days — book renewal")
    except Exception:
        days_to_expiry = -1
        issues.append("Invalid expiry date — verify with CPCS lookup")

    if "Appointed Person" not in " ".join(qualifications) and "AP" not in qualifications:
        issues.append("No documented AP training course in qualifications")
    if years_experience < 2:
        issues.append("Less than 2 years AP experience — pair with senior AP for complex/critical lifts")

    return _attestation({
        "tool": "check_ap_competence",
        "name": name,
        "a88_cpcs_card": a88_cpcs_card_number,
        "days_to_card_expiry": days_to_expiry,
        "qualifications_listed": qualifications,
        "years_experience": years_experience,
        "competent_for": (
            ["basic", "standard"] if not issues
            else (["basic"] if "EXPIRED" not in " ".join(issues) else [])
        ),
        "issues": issues,
    })


@mcp.tool()
def validate_lift_plan(
    has_load_weight: bool = False,
    has_swl_check: bool = False,
    has_ground_assessment: bool = False,
    has_exclusion_zone: bool = False,
    has_method_statement: bool = False,
    has_emergency_procedure: bool = False,
    has_ap_signoff: bool = False,
    has_toolbox_talk_record: bool = False,
    has_weather_cutoff: bool = False,
    has_communications_plan: bool = False,
) -> dict:
    """Score a lift plan for BS 7121 compliance — Principal Contractor review."""
    checks = {
        "load_weight": has_load_weight,
        "swl_check": has_swl_check,
        "ground_assessment": has_ground_assessment,
        "exclusion_zone": has_exclusion_zone,
        "method_statement": has_method_statement,
        "emergency_procedure": has_emergency_procedure,
        "ap_signoff": has_ap_signoff,
        "toolbox_talk_record": has_toolbox_talk_record,
        "weather_cutoff": has_weather_cutoff,
        "communications_plan": has_communications_plan,
    }
    passed = sum(checks.values())
    total = len(checks)
    pct = round(100.0 * passed / total, 1)

    if pct >= 90: grade, advice = "A", "Pass — Principal Contractor ready"
    elif pct >= 70: grade, advice = "B", "Minor gaps — close before mobilisation"
    elif pct >= 50: grade, advice = "C", "Substantial gaps — DO NOT proceed without AP re-review"
    else: grade, advice = "F", "Insufficient — restart planning"

    return _attestation({
        "tool": "validate_lift_plan",
        "checks": checks,
        "passed": passed, "total": total,
        "compliance_pct": pct,
        "grade": grade,
        "advice": advice,
        "missing": [k for k, v in checks.items() if not v],
    })


@mcp.tool()
def calculate_ground_bearing_pressure(
    crane_mass_kg: float,
    counterweight_mass_kg: float,
    load_mass_kg: float,
    radius_m: float,
    outrigger_pad_area_m2: float = 1.0,
    soil_safe_bearing_kpa: float = 100.0,
) -> dict:
    """Estimate ground bearing pressure under outriggers + assess against soil.

    This is a SIMPLIFIED estimate — competent person must validate.
    """
    total_kg = crane_mass_kg + counterweight_mass_kg + load_mass_kg
    # Worst case ~60% on one outrigger pad at full radius (rough heuristic)
    worst_kg_per_pad = total_kg * 0.6
    pressure_kpa = (worst_kg_per_pad * 9.81 / 1000.0) / max(0.01, outrigger_pad_area_m2)

    if pressure_kpa > soil_safe_bearing_kpa * 1.5:
        verdict = "CRITICAL — pad area or soil-improvement required"
    elif pressure_kpa > soil_safe_bearing_kpa:
        verdict = "EXCEEDS soil safe bearing — enlarge pad or improve subgrade"
    else:
        verdict = "Within soil safe bearing — proceed (verify with competent ground engineer)"

    return _attestation({
        "tool": "calculate_ground_bearing_pressure",
        "total_mass_kg": total_kg,
        "worst_outrigger_kg": worst_kg_per_pad,
        "pressure_kpa": round(pressure_kpa, 1),
        "soil_safe_bearing_kpa": soil_safe_bearing_kpa,
        "verdict": verdict,
        "advisory": "Heuristic only. Lifting Operations engineer must validate against actual soil report.",
    })


@mcp.tool()
def check_exclusion_zone(
    radius_m: float,
    load_height_m: float = 0.0,
    load_drop_safety_factor: float = 1.2,
) -> dict:
    """Compute minimum exclusion zone radius for a lift."""
    drop_zone_m = max(radius_m * 1.1, load_height_m * load_drop_safety_factor)
    return _attestation({
        "tool": "check_exclusion_zone",
        "minimum_radius_m": round(drop_zone_m, 1),
        "barrier_required": True,
        "signage_required": True,
        "designated_signaller_required": True,
        "advisory": "Barrier must be physical (Heras fencing or equivalent). Signs at every approach.",
    })


@mcp.tool()
def schedule_loler_thorough_exam(
    equipment_type: str,
    equipment_id: str,
    last_te_date: str = "",
    used_for_personnel: bool = False,
) -> dict:
    """LOLER 1998 Reg 9 Thorough Examination cadence.

    Args:
      equipment_type: 'mobile_crane' / 'tower_crane' / 'lorry_loader' / 'hoist' / 'sling' / 'chain'
      used_for_personnel: 6-monthly interval if used for lifting people
    """
    interval_months = 6 if used_for_personnel else 12
    # Accessories are 6-monthly regardless under LOLER Schedule 1
    if equipment_type in ("sling", "chain", "shackle", "hook"):
        interval_months = 6

    try:
        last = date.fromisoformat(last_te_date)
    except Exception:
        last = None

    if last:
        next_due = date.fromordinal(last.toordinal() + interval_months * 30)
        days_to_next = (next_due - date.today()).days
        overdue = days_to_next < 0
    else:
        next_due, days_to_next, overdue = None, None, True

    return _attestation({
        "tool": "schedule_loler_thorough_exam",
        "equipment_type": equipment_type,
        "equipment_id": equipment_id,
        "interval_months": interval_months,
        "last_te": last_te_date or "unknown",
        "next_due": next_due.isoformat() if next_due else "schedule immediately",
        "days_to_next": days_to_next,
        "overdue": overdue,
        "regulator_ref": "LOLER 1998 Reg 9 + Schedule 1",
        "advisory": (
            "OVERDUE — DO NOT USE in lifting operations until competent TE complete."
            if overdue else "Plan downtime around the next-due date."
        ),
    })


@mcp.tool()
def check_cpcs_card(
    card_number: str,
    card_category: str,
    expiry_date: str,
) -> dict:
    """Check a CPCS operator card category + expiry.

    Args:
      card_category: e.g. 'A40' (mobile crane), 'A36' (lorry loader),
                     'A73' (slinger/signaller), 'A88' (AP)
    """
    cat_label = CPCS_CATEGORIES.get(card_category.upper(), "Unknown CPCS category")
    try:
        exp = date.fromisoformat(expiry_date)
        days_to_expiry = (exp - date.today()).days
        valid = days_to_expiry > 0
    except Exception:
        days_to_expiry = -1; valid = False

    issues = []
    if not valid: issues.append("CARD EXPIRED — operator cannot operate")
    elif days_to_expiry < 30: issues.append(f"Expires in {days_to_expiry} days — schedule CITB Test + renewal")

    return _attestation({
        "tool": "check_cpcs_card",
        "card_number": card_number,
        "category": card_category.upper(),
        "category_label": cat_label,
        "days_to_expiry": days_to_expiry,
        "valid": valid,
        "issues": issues,
    })


@mcp.tool()
def check_cap1096_aviation(
    crane_height_agl_m: float,
    site_postcode: str = "",
    within_6km_of_aerodrome: bool = False,
) -> dict:
    """Civil Aviation Act §50 / CAP 1096 — tall crane near aerodrome notification.

    Args:
      crane_height_agl_m: top of crane above ground level (meters)
      within_6km_of_aerodrome: per CAA guidance, 6km is the safeguarded zone
    """
    notify_required = (
        crane_height_agl_m >= CAA_SECTION_50_THRESHOLD_M
        and within_6km_of_aerodrome
    ) or crane_height_agl_m >= 91.4  # 300ft general aviation threshold

    return _attestation({
        "tool": "check_cap1096_aviation",
        "crane_height_agl_m": crane_height_agl_m,
        "within_6km_of_aerodrome": within_6km_of_aerodrome,
        "notification_required": notify_required,
        "regulator_ref": "Civil Aviation Act 1982 §50 + CAP 1096",
        "lights_required": notify_required and crane_height_agl_m >= 45.0,
        "advisory": (
            "Notify CAA via NATS AIS + relevant aerodrome safeguarding office at least "
            "28 days before erection. Aviation obstacle lighting per CAP 168."
            if notify_required else "Below notification threshold for stated context."
        ),
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
