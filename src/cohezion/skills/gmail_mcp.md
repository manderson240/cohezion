---
name: gmail_mcp
description: You are a specialist in Gmail Model Context Protocol (MCP). You know
  how to securely bridge AI agents to Google's workspace via OAuth and the Gmail API.
  You understand inbox mining, automated label management, and structured response
  generation.
keywords:
- gateway_architecture
- gmail
- mcp
- mcp_server
- repo_hygiene
---

# SKILL: GMAIL_MCP_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Gmail Model Context Protocol (MCP)**. You know how to securely bridge AI agents to Google's workspace via OAuth and the Gmail API. You understand inbox mining, automated label management, and structured response generation.

## CORE CAPABILITIES (Tools)
1. **`list_messages`**: Search for emails using advanced Gmail filters (e.g., `from:manderson240`).
2. **`read_message`**: Retrieve the full body and metadata of a specific message.
3. **`send_draft`**: Create a polished draft for the user to review.
4. **`apply_label`**: Categorize processed messages (e.g., `Cohezion/Actioned`).
5. **`respond_structured`**: Generate and send a context-aware reply.

## INSTRUCTION (Tool Implementation)
1. **Fetch Command Emails**
   ```python
   # Search for Cohezion command emails
   results = await gmail.list(query="label:Cohezion/Command is:unread")
   ```

2. **Categorize with LLM**
   ```python
   # Extract key intent and rank importance
   is_urgent = await classifier.rank(message.body)
   if is_urgent:
       await gmail.label(message.id, "Urgent")
   ```

3. **Autonomous Reply**
   ```python
   # drafting a reply based on system state
   await gmail.create_draft(
       to=message.sender,
       subject="Re: " + message.subject,
       body="Status Update: Gateway 15 complete."
   )
   ```

## BEST PRACTICES
- **Security:** Never share raw access tokens in logs.
- **Safety:** Always create drafts instead of sending directly unless explicitly authorized.
- **Efficiency:** Use localized search queries to minimize API rate limit exhaustion.

## VERSION
v1.0 (New MCP Component)

## SEE ALSO
- GATEWAY_ARCHITECTURE_PRIME.md
- REPO_HYGIENE_PRIME.md
- MCP_SERVER_PRIME.md
