# SKILL: ASYNC_WORKFLOW_PRIME

## DOMAIN EXPERTISE
Asynchronous task queue using Google Keep or local file, with email notifications.

## SETUP

### Google Keep Integration
1. Install gkeepapi: `pip install gkeepapi`
2. Create app password: https://myaccount.google.com/apppasswords
3. Get master token: Use gpsoauth or keep-mcp token generator
4. Set environment:
   ```bash
   export GOOGLE_EMAIL="your.email@gmail.com"
   export GOOGLE_KEEP_TOKEN="your-master-token"
   ```

### Email Notifications
1. Enable 2FA on Gmail
2. Create app password
3. Set environment:
   ```bash
   export NOTIFICATION_EMAIL="sender@gmail.com"
   export NOTIFICATION_PASSWORD="app-password"
   export NOTIFICATION_RECIPIENT="you@email.com"
   ```

### Local Fallback
If Google Keep not configured, uses `.cohezion/tasks.md`:
```markdown
- [ ] Task to do
- [x] Completed task
```

## USAGE

### Check Queue
```bash
python -m cohezion.mcp.async_workflow check
```

### Run Pending Tasks
```bash
python -m cohezion.mcp.async_workflow run
```

### Task Keywords
| Keyword | Handler |
|---------|---------|
| simulate | Run simulations |
| debate | Democratic debate |
| analyze | Semantic analysis |
| audit | Platform audit |
| test | Run pytest |

## SEE ALSO
- keep_integration.py
- email_notifier.py
- async_workflow.py
