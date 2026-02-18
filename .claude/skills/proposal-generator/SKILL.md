---
name: proposal-generator
description: Generate professional PandaDoc proposals from structured input or sales call transcripts. Use when user asks to create a proposal, generate a client proposal, or build a sales proposal.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Proposal Generator

## Goal
Generate professional PandaDoc proposals from structured client data or sales call transcripts, with expanded problem/benefit sections, automated creation, and follow-up email.

## Prerequisites
- `PANDADOC_API_KEY` in `.env`
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/proposal-generator/create_proposal.py <<'EOF'
{
  "client": {
    "firstName": "John",
    "lastName": "Smith",
    "email": "john@company.com",
    "company": "Company Inc"
  },
  "project": {
    "title": "Growth Partnership",
    "problems": {"problem01": "Low conversion rate", "problem02": "No lead pipeline", "problem03": "Weak positioning", "problem04": "Manual outreach"},
    "benefits": {"benefit01": "Automated lead gen", "benefit02": "Conversion optimization", "benefit03": "Market positioning", "benefit04": "Scalable outreach"},
    "monthOneInvestment": "$5,000",
    "monthTwoInvestment": "$5,000",
    "monthThreeInvestment": "$5,000"
  },
  "generated": {
    "slideFooter": "Confidential | Company Inc Strategic Initiative | 2026-02",
    "contractFooterSlug": "CompanyInc-GrowthPartnership-2026-02",
    "createdDate": "2026-02-17"
  }
}
EOF
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_client_proposals_pitch_decks.md`
4. **Gather Information** - From structured bullet points or sales call transcript
5. **Research Client** - Optionally fetch client website for brand voice context
6. **Generate Content** - Expand problems into strategic paragraphs, benefits into implementation-focused paragraphs (direct "you" language, revenue-impact focus)
7. **Execute Proposal Creation** - Run script with JSON input to create PandaDoc proposal
8. **Send Follow-Up Email** - HTML-formatted recap email to client
9. **Notify** - Share PandaDoc internal link for review

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `input_file` | No | JSON file with proposal data (or pass via stdin) |

## Quality Checklist
- [ ] All 4 problems expanded with revenue-impact language
- [ ] All 4 benefits expanded with implementation focus
- [ ] Direct "you" language throughout (no third-person)
- [ ] Investment breakdown clearly stated
- [ ] Slide footer and contract slug generated
- [ ] PandaDoc proposal created successfully
- [ ] Follow-up email sent in HTML format

## Related Directives
- `directives/create_proposal.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_proposals_pitch_decks.md`
- `skills/SKILL_BIBLE_agency_sales_system.md`
- `skills/SKILL_BIBLE_high_ticket_sales_process.md`
- `skills/SKILL_BIBLE_sales_closing_mastery.md`
