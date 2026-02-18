---
name: n8n-converter
description: Convert n8n workflow JSON files into directives and execution scripts. Use when user asks to convert n8n workflow, parse n8n JSON, import n8n automation, or generate directive from workflow file.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# N8N Workflow Converter

## Goal
Parse an n8n workflow JSON file and generate a markdown directive (SOP) plus optional Python execution scripts, following the 3-layer DOE architecture.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env` (for parsing complex workflows)

## Execution Command

```bash
python3 .claude/skills/n8n-converter/convert_n8n_to_directive.py \
  "path/to/workflow.json"
```

### Batch Convert All Workflows in a Directory

```bash
python3 .claude/skills/n8n-converter/convert_n8n_to_directive.py \
  "path/to/workflows/" \
  --batch
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Identify Workflow File** - Locate the n8n JSON file at the provided path
3. **Run Converter** - Execute `.claude/skills/n8n-converter/convert_n8n_to_directive.py` which extracts trigger info, node sequences, AI agent prompts, API integrations, and output schemas
4. **Review Generated Directive** - Check the output in `directives/` for completeness
5. **Review Generated Script** - If API operations exist, check the output in `.claude/skills/n8n-converter/`
6. **Refine** - Add any missing context, clarify ambiguous steps, add error handling notes

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `workflow_path` | Yes | Path to n8n workflow JSON file or directory |
| `--batch` | No | Convert all workflows in a directory |

## Quality Checklist
- [ ] Directive includes trigger type, inputs, process steps, and output schema
- [ ] AI agent prompts are extracted and documented
- [ ] API integrations are identified and scripted
- [ ] Edge cases and error handling are noted
- [ ] Generated files follow snake_case naming convention

## Related Directives
- `directives/convert_n8n_workflow.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_n8n_workflow_building.md`
- `skills/SKILL_BIBLE_n8n_workflow_automation.md`
- `skills/SKILL_BIBLE_n8n_triggers_agents.md`
- `skills/SKILL_BIBLE_n8n_import_modify.md`
