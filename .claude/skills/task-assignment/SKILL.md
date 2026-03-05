---
name: task-assignment
description: Automatically assign tasks to team members based on skills and capacity. Use when user asks to assign tasks, distribute work, balance team workload, or allocate team resources.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Team Task Assignment

## Goal
Automatically assign tasks to team members based on skills match, current capacity, workload balance, and past performance using AI-powered optimization.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI-powered assignment optimization

## Execution Command

```bash
python3 .claude/skills/task-assignment/assign_team_tasks.py \
  --tasks tasks.json \
  --team team.json \
  --output .tmp/assignments.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Data** - Ensure tasks JSON and team JSON are formatted correctly
4. **Run Assignment Script** - Execute with tasks and team data
5. **Review Assignments** - Verify balanced distribution and skill matching

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--tasks` | Yes | JSON file or string with task list (each task: name, skills, priority, hours) |
| `--team` | Yes | JSON file or string with team members (each: name, skills, capacity, current_load) |
| `--output` | No | Output file path (default: .tmp/assignments.md) |

## Quality Checklist
- [ ] All tasks assigned to a team member
- [ ] Skills match between task requirements and assignee capabilities
- [ ] No team member overloaded beyond capacity
- [ ] Priority tasks assigned to most capable members
- [ ] Assignment rationale provided for each task
- [ ] Summary includes per-member workload breakdown

## Related Directives
- `directives/team_task_assignment.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_project_management.md`
- `skills/SKILL_BIBLE_agency_operations.md`
