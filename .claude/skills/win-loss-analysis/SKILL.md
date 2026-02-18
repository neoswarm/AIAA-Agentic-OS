---
name: win-loss-analysis
description: Analyze won and lost deals to identify patterns and improve close rates. Use when user asks to analyze sales performance, review win/loss data, identify deal patterns, or improve close rates.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Win/Loss Analysis

## Goal
Analyze closed deals (won and lost) to identify winning patterns, common loss reasons, competitor insights, and segment-level performance, producing an actionable report with recommendations to improve close rates.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI-powered pattern analysis

## Execution Command

```bash
python3 .claude/skills/win-loss-analysis/analyze_win_loss.py \
  --deals deals.json \
  --period "Last Quarter" \
  --output .tmp/win_loss_analysis.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Deal Data** - Ensure deals JSON file has won/lost deals with metadata
4. **Run Analysis** - AI identifies patterns across wins, losses, segments
5. **Review Report** - Verify insights are data-backed and recommendations actionable

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--deals` | Yes | JSON file with deal data or summary text (can also pass text directly) |
| `--period` | No | Analysis period label (default: "Last Quarter") |
| `--output` | No | Output file path (default: .tmp/win_loss_analysis.md) |

## Quality Checklist
- [ ] Executive summary with win rate and key findings
- [ ] Wins analysis with common characteristics and patterns
- [ ] Losses analysis with top reasons and competitor breakdown
- [ ] Segment analysis by deal size, industry, and lead source
- [ ] Actionable recommendations (at least 3)
- [ ] Data tables with metrics (win rate, deal values, counts)
- [ ] Key insights clearly prioritized

## Related Directives
- `directives/win_loss_analysis.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_sales_analytics.md`
- `skills/SKILL_BIBLE_agency_sales_system.md`
