---
name: lead-deduplication
description: Remove duplicate leads from CSV or JSON lists using email, domain, or fuzzy matching. Use when user asks to deduplicate leads, clean lead lists, remove duplicates, or merge lead files.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead Deduplication

## Goal
Remove duplicate leads across one or more lists using configurable matching keys (email, LinkedIn URL, domain, phone). Output a clean, deduplicated list.

## Prerequisites
- Python 3.10+
- Input file in CSV or JSON format

## Execution Command

```bash
python3 .claude/skills/lead-deduplication/dedupe_leads.py \
  --input leads.csv \
  --keys "email,linkedin_url" \
  --keep first \
  --output .tmp/deduped_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Identify Input Files** - Locate CSV or JSON lead files to deduplicate
4. **Choose Match Keys** - Select deduplication fields (email, domain, phone, linkedin_url)
5. **Run Deduplication** - Script compares leads on composite keys, case-insensitive
6. **Review Results** - Check duplicate count and verify no valid leads removed
7. **Export Clean List** - Output deduplicated JSON with stats

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--input` | Yes | Input file path (CSV or JSON) |
| `--keys` | No | Comma-separated dedup keys (default: "email") |
| `--keep` | No | Which duplicate to keep: "first" or "last" (default: "first") |
| `--output` | No | Output path (default: `.tmp/deduped_leads.json`) |

## Quality Checklist
- [ ] Input file loaded successfully with correct format
- [ ] Dedup keys match available columns in the data
- [ ] Duplicate count reported in output
- [ ] No valid unique leads accidentally removed
- [ ] Output includes dedup stats (original count, removed, remaining)

## Related Directives
- `directives/lead_deduplication.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
