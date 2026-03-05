---
name: youtube-to-campaign
description: Master pipeline that mines YouTube knowledge and generates full marketing campaigns with deployed agents. Use when user asks to learn from YouTube and run a campaign, create a YouTube-to-campaign pipeline, mine YouTube for campaign knowledge, or deploy campaign agents.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube to Campaign Pipeline

## Goal
Combine YouTube knowledge mining with full campaign generation. Learn best practices from top YouTube experts, create skill bibles, and execute multi-phase campaigns with learned knowledge — optionally deploying specialized agents for parallel work.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI generation (Claude)
- `OPENAI_API_KEY` in `.env` — Whisper transcription
- `PERPLEXITY_API_KEY` in `.env` — Research (optional)
- YouTube Data API enabled

## Execution Command

```bash
python3 .claude/skills/youtube-to-campaign/youtube_to_campaign_pipeline.py \
  --client "Acme Corp" \
  --website "https://acmecorp.com" \
  --offer "AI Lead Generation" \
  --learn-from-youtube \
  --deploy-agents 10
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Check Existing Skills** - Scan `skills/` for existing skill bibles to avoid re-mining
4. **YouTube Knowledge Mining** - For each campaign phase, search top channels, get best videos, transcribe, convert to how-to manuals, and generate skill bibles
5. **Campaign Generation** - Run 8-phase pipeline: client research → Meta ads setup → ad copy → ad images → landing page → landing page images → CRM pipeline → follow-up sequences
6. **Agent Deployment** - Deploy specialized agents (research, ad copy, creative, landing page, CRM, email) for parallel execution
7. **Quality Review** - Verify all phases completed and outputs saved
8. **Deliver Results** - Save to `.tmp/youtube_campaign_pipeline/` with master results JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes* | Client/company name (*unless --skip-campaign) |
| `--website` | Yes* | Client website |
| `--offer` | Yes* | Main offer/product |
| `--budget` | No | Monthly ad budget (default: 5000) |
| `--learn-from-youtube` | No | Mine YouTube first (flag) |
| `--phases` | No | Specific phases to learn (e.g., client_research meta_ads_setup ad_copy) |
| `--deploy-agents` | No | Number of agents to deploy (default: 0) |
| `--skip-campaign` | No | Only learn, no campaign (flag) |
| `--output-dir` | No | Output directory (default: .tmp/youtube_campaign_pipeline) |
| `--parallel` | No | Parallel processing level (default: 3) |

## Quality Checklist
- [ ] At least 5/7 skill bibles generated (if learning)
- [ ] All 8 campaign phases complete (if running campaign)
- [ ] Agents deployed successfully (if requested)
- [ ] All output files saved to output directory
- [ ] Master results JSON created

## Related Directives
- `directives/youtube_to_campaign_pipeline.md`
- `directives/youtube_knowledge_miner.md`
- `directives/full_campaign_pipeline.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_lead_generation.md`
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_ad_copywriting.md`
- `skills/SKILL_BIBLE_landing_page_copywriting.md`
- `skills/SKILL_BIBLE_email_sequence_writing.md`
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
