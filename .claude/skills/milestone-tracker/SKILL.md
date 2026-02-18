---
name: milestone-tracker
description: Track project milestones and generate progress reports with completion percentages and overdue alerts. Use when user asks to track milestones, check project progress, generate milestone report, or review project status.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Project Milestone Tracker

## Goal
Track project milestones from a JSON data source, calculate completion percentages, identify overdue items, and generate a formatted progress report.

## Prerequisites
- Milestones data in JSON format (file or inline)

## Execution Command

```bash
python3 .claude/skills/milestone-tracker/track_project_milestones.py \
  --project "Website Redesign" \
  --milestones milestones.json \
  --output .tmp/milestone_report.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Milestones** - Read milestones from JSON file or inline JSON string
4. **Calculate Stats** - Count completed, in-progress, pending, and overdue items
5. **Generate Progress Bar** - Visual progress indicator
6. **Build Report** - Markdown report with summary table and milestone details
7. **Flag Overdue** - Highlight milestones past their due date
8. **Save Output** - Write formatted report to file

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--project` | Yes | Project name |
| `--milestones` | Yes | Path to milestones JSON file or inline JSON string |
| `--output` | No | Output path (default: `.tmp/milestone_report.md`) |

### Milestones JSON Format
```json
[
  {
    "name": "Design Complete",
    "status": "completed",
    "due_date": "2026-01-15",
    "completed_date": "2026-01-14"
  },
  {
    "name": "Development Sprint 1",
    "status": "in_progress",
    "due_date": "2026-02-01"
  }
]
```

## Quality Checklist
- [ ] All milestones loaded and categorized correctly
- [ ] Progress percentage calculated accurately
- [ ] Overdue milestones flagged with due dates
- [ ] Report includes summary table and detail sections
- [ ] Output readable and client-presentable

## Related Directives
- `directives/project_milestone_tracker.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_reporting_dashboards.md`
