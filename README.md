<!-- mcp-name: io.github.CSOAI-ORG/meok-bs7121-mcp -->
[![MCP Scorecard: 90/100](https://img.shields.io/badge/proofof.ai-90%2F100-5b21b6)](https://proofof.ai/scorecard/meok-bs7121-mcp.html)

# meok-bs7121-mcp

> BS 7121 lift-plan compliance for UK crane + hiab operators. Parts 1/3/4/5/7 clause lookup, AP competence, CPA Contract-Lift vs Hire triage, GBP calc, LOLER scheduling. By **MEOK AI Labs**.

## Why this exists

BS 7121 is the UK lift-planning bible. Five parts most operators reference daily. Plus LOLER, PUWER, CDM 2015, CPCS. Mobile, tower, crawler, lorry-loader — every category has its own triage.

Real UK cases this MCP exists to prevent:
- **Brand Energy & Infrastructure Services UK — £1.6m HSE fine** (Nov 2024). Jack Phillips (24) killed Eastbourne. Expired sling + missing exclusion zone.
- **Baldwins Crane Hire v Vision Modular Systems** (ongoing 2026, £951k claim). CPA Condition 9(d) — proves Contract-Lift vs Hire triage at the QUOTE stage is the £100k+ wedge.

This MCP sits ABOVE 3D Lift Plan and Lolerflow — it doesn't simulate; it validates, classifies, and produces audit-quality compliance attestations.

## Install

```bash
pip install meok-bs7121-mcp
```

## Tools (10)

| Tool | Use case |
|------|----------|
| `lookup_bs7121_clause` | Quick clause lookup across parts 1/3/4/5/7 |
| `classify_lift_category` | basic / standard / complex / critical — AP signoff trigger |
| `triage_cpa_hire_vs_contract_lift` | The £100k+ wedge — Baldwins v Vision style |
| `check_ap_competence` | A88 card + qualifications + experience |
| `validate_lift_plan` | 10-point Principal Contractor review |
| `calculate_ground_bearing_pressure` | Outrigger pressure vs soil safe bearing |
| `check_exclusion_zone` | Minimum radius + barrier/signaller requirements |
| `schedule_loler_thorough_exam` | LOLER Reg 9 cadence (6mo personnel / 12mo other) |
| `check_cpcs_card` | A02/A36/A40/A60/A66/A73/A85/A88 verification |
| `check_cap1096_aviation` | CAA §50 notification for cranes near aerodromes |

## Pricing

- **Free** — MIT self-host
- **Starter** — £99/mo (lift plans + LOLER tracking)
- **Pro** — £299/mo (CPA Contract Lift triage + multi-AP + audit pack)
- **Enterprise** — £799/mo (multi-depot, SSO, Principal Contractor API)

## Regulatory basis

- BS 7121-1:2016, -3:2017, -4:2010, -5:2019, -7:2020
- LOLER 1998 (SI 1998/2307)
- PUWER 1998 (SI 1998/2306)
- CDM 2015 (SI 2015/51)
- CAA Civil Aviation Act 1982 §50, CAP 1096
- CPA Model Conditions of Hire 2011 + 2021 amendments

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)


## Configuration

Add to your `claude_desktop_config.json` (Claude Desktop) or your MCP client config:

```json
{
  "mcpServers": {
    "meok-bs7121-mcp": {
      "command": "uvx",
      "args": ["meok-bs7121-mcp"]
    }
  }
}
```

Or: `pip install meok-bs7121-mcp` then run the `meok-bs7121-mcp` command (stdio transport).

## Examples

Once configured, ask your assistant, for example:
- "Use `lookup_bs7121_clause` to …"
- "Use `classify_lift_category` to …"
- "Use `triage_cpa_hire_vs_contract_lift` to …"


<!-- GEO-FOOTER:v1 -->

---

### Part of the MEOK constellation

This MCP is one node in a connected ecosystem built by **MEOK AI LABS** around a single
sovereign AI core — governed agents with a hash-chained audit trail, mapped to the CSOAI
compliance charter.

- 🌐 The whole map: **<https://meok.ai/constellation>**
- 🛡️ AI governance & certification: **<https://councilof.ai>** · **<https://csoai.org>**
- ✅ Verify any signed report: **<https://meok.ai/verify>**
