---
name: google-doc-delivery
description: Upload markdown content to formatted Google Docs for client delivery. Use when user asks to create a Google Doc, deliver content, or share documents.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Google Doc Delivery

## Goal
Convert markdown content to formatted Google Docs and share for client delivery. Handles OAuth and service account authentication.

## Prerequisites
- `GOOGLE_APPLICATION_CREDENTIALS` or `credentials.json` in project root
- `token.pickle` for OAuth (generated on first run)
- `SLACK_WEBHOOK_URL` for delivery notifications (optional)

## Execution Commands

```bash
# Create Google Doc from markdown file
python3 .claude/skills/google-doc-delivery/create_google_doc.py \
  --file ".tmp/output.md" \
  --title "Deliverable Title"

# With folder and sharing
python3 .claude/skills/google-doc-delivery/create_google_doc.py \
  --file ".tmp/output.md" \
  --title "Client Deliverable" \
  --folder_id "google_drive_folder_id" \
  --share "client@email.com"
```

## Process Steps
1. **Authenticate** - OAuth flow or service account credentials
2. **Parse Markdown** - Convert markdown to Google Docs formatting
3. **Create Document** - Create new Google Doc with title
4. **Apply Formatting** - Headers, bold, italic, links, lists
5. **Move to Folder** - Optional: move to specific Drive folder
6. **Share** - Optional: share with client email
7. **Notify** - Send Slack notification with doc link
8. **Return URL** - Output the document URL

## Formatting Support
- H1, H2, H3 headers with proper sizing
- Bold and italic text
- Bullet and numbered lists
- Links (clickable)
- Code blocks (monospace)

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--file` | Yes | Path to markdown file |
| `--title` | Yes | Google Doc title |
| `--folder_id` | No | Google Drive folder ID |
| `--share` | No | Email to share with |

## Quality Checklist
- [ ] Authentication succeeds
- [ ] Markdown properly converted to Docs format
- [ ] Headers and formatting preserved
- [ ] Document created and accessible
- [ ] Shared with correct recipients
- [ ] Slack notification sent (if configured)

## Related Directives
- `directives/google_doc_creator.md`
- `directives/formatted_google_doc_creator.md`
