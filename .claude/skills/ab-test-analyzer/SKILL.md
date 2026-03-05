---
name: ab-test-analyzer
description: Analyze A/B test results with statistical significance calculations and clear recommendations. Use when user asks to analyze an A/B test, check test significance, or evaluate split test results.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# A/B Test Analyzer

## Goal
Analyze A/B test results by calculating conversion rates, statistical significance, confidence levels, and generating clear implement/continue/stop recommendations.

## Prerequisites
- Python 3.10+ with `scipy` and `numpy` installed

## Execution Command

```bash
python3 .claude/skills/ab-test-analyzer/generate_ab_test_analysis.py \
  --control '{"visitors": 5000, "conversions": 250}' \
  --variant '{"visitors": 5000, "conversions": 325}' \
  --test_name "Homepage CTA Button" \
  --output ".tmp/ab_analysis.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_email_ab_testing.md`
4. **Parse Test Data** - Extract control and variant metrics from JSON input
5. **Calculate Metrics** - Conversion rates, lift percentage, sample sizes
6. **Statistical Tests** - Chi-square test for significance, p-value calculation
7. **Determine Confidence** - Calculate confidence level against target (typically 95%)
8. **Generate Recommendation** - Implement (>95% confidence + >10% lift), Continue (<95%), or Stop (negative lift)
9. **Project Impact** - Estimate monthly impact of implementing variant
10. **Output** - Save analysis report to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--control` | Yes | Control group JSON: `{"visitors": N, "conversions": N}` |
| `--variant` | Yes | Variant group JSON: `{"visitors": N, "conversions": N}` |
| `--test_name` | No | Test name for report header (default: `A/B Test`) |
| `--output` | No | Output file path (default: `.tmp/ab_analysis.md`) |

## Quality Checklist
- [ ] Conversion rates calculated correctly for both groups
- [ ] Lift percentage accurate (variant vs control)
- [ ] Statistical significance test performed (chi-square)
- [ ] P-value and confidence level reported
- [ ] Clear recommendation: Implement / Continue Testing / Stop
- [ ] Sample size adequacy noted
- [ ] Projected monthly impact included
- [ ] Caveats mentioned (duration, seasonality, external factors)

## Related Directives
- `directives/ab_test_analyzer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_email_ab_testing.md`
- `skills/SKILL_BIBLE_cold_email_analytics.md`
- `skills/SKILL_BIBLE_marketing_strategy_advanced.md`
