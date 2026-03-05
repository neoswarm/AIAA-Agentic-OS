# Context Loading Rules

## CRITICAL: Always load agency context BEFORE generating any content.

## Agency Context (`context/`)
| File | Load When |
|------|-----------|
| `agency.md` | ALWAYS — agency identity, positioning, mission |
| `owner.md` | Content with personal brand, proposals |
| `brand_voice.md` | ANY content creation — tone, style, vocabulary |
| `services.md` | Proposals, pitches, pricing discussions |

## Client Context (`clients/{client_name}/`)
| File | Purpose |
|------|---------|
| `profile.md` | Business info, industry, goals, audience, competitors |
| `rules.md` | MUST-FOLLOW rules — words to use/avoid, compliance, formatting |
| `preferences.md` | Style preferences, tone, formatting standards |
| `history.md` | Past projects, outcomes, learnings |

**Load ALL client files when doing ANY work for that client.**

## Skill Bibles (`skills/SKILL_BIBLE_*.md`)
- Load relevant ones BEFORE execution for domain expertise
- Find them: `ls skills/ | grep -i "<topic>"`
- Key categories: VSL/funnels, cold email, agency/sales, AI/automation

## Directives (`directives/*.md`)
- Load the primary directive for the workflow
- Check "Related Directives" section for dependencies

## Loading Order
```
1. context/agency.md        → Who you represent
2. context/brand_voice.md   → How you communicate
3. clients/{name}/*.md      → Client rules (if applicable)
4. skills/SKILL_BIBLE_*     → Domain expertise
5. directives/<workflow>.md → SOP steps
6. execution/<script>.py    → What to run
```

## Anti-Patterns
- ❌ Generating content without loading agency context
- ❌ Client work without loading client rules
- ❌ Running scripts without reading the directive first
- ❌ Loading 10+ context files (context pollution — keep it focused)
