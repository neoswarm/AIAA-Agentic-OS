# Delivery Pipeline

## Standard 3-Step Delivery
Every deliverable follows this pipeline:

### Step 1: Save Locally
- Save to `.tmp/<project>/<filename>.md`
- Use descriptive names: `01_research.md`, `02_vsl_script.md`
- Checkpoints enable resume on failure

### Step 2: Create Google Doc
```bash
python3 execution/create_google_doc.py --file ".tmp/output.md" --title "Doc Title"
```
- Use native Google Docs formatting, NOT markdown
- Requires `credentials.json` + `token.pickle` in project root

### Step 3: Slack Notification
```bash
python3 execution/send_slack_notification.py --message "Task complete" --channel "#general"
```
- Include Google Doc link in message
- Don't send duplicate notifications within 5 minutes

## Delivery Rules
- ALWAYS save locally first (backup before delivery)
- If Google Docs fails → continue, report error, file is safe locally
- If Slack fails → continue, delivery is done, notification is secondary
- Degrade gracefully: local > Docs > Slack (priority order)

## Output Organization
```
.tmp/
├── vsl_funnel_acme/
│   ├── 01_research.md
│   ├── 02_vsl_script.md
│   ├── 03_sales_page.md
│   └── 04_email_sequence.md
├── cold_emails_xyz/
│   └── emails.md
└── research_target/
    └── report.md
```
