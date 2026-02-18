# Error Handling Patterns

## API Failures — Retry with exponential backoff
```python
for attempt in range(3):
    try:
        result = api_call()
        break
    except Exception as e:
        if attempt == 2:
            raise
        time.sleep(10 * (attempt + 1))
```

## Missing Inputs — Fail fast
```python
if not args.required_field:
    print("Error: --required_field is required")
    sys.exit(1)
```

## Partial Failures — Degrade gracefully
| Severity | Action |
|----------|--------|
| Critical workflow fails | Stop and report immediately |
| Non-critical step fails | Continue with warning |
| Delivery fails | Save locally, continue |
| Notification fails | Log it, don't block |

## Common Failure Modes
| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Bad/expired API key | Check .env, refresh token |
| `429 Rate Limited` | Too many API calls | Add backoff, reduce frequency |
| `timeout` | Slow API or large payload | Increase timeout, chunk input |
| `ModuleNotFoundError` | Missing pip package | `pip install -r requirements.txt` |
| `FileNotFoundError` | Missing input file | Check .tmp/ for upstream output |
| `JSONDecodeError` | Malformed API response | Log raw response, retry |

## Debugging Commands
```bash
python3 execution/<script>.py --help          # Check arguments
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"  # Test API
railway logs                                    # Dashboard logs
```

## Rule: Never swallow errors silently. Log, warn, or fail — pick one.
