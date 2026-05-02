#!/usr/bin/env python3
"""Send the application summary email to manderson240@gmail.com.

Usage:
    # Set your Gmail App Password first (NOT your regular password):
    # 1. Go to https://myaccount.google.com/apppasswords
    # 2. Generate an app password for "Mail"
    # 3. Run:
    export GMAIL_APP_PASSWORD="your-16-char-app-password"
    python scripts/send_summary_email.py
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def main():
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        print("ERROR: Set GMAIL_APP_PASSWORD environment variable first.")
        print()
        print("Steps:")
        print("  1. Go to https://myaccount.google.com/apppasswords")
        print("  2. Generate an app password for 'Mail'")
        print("  3. export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
        print("  4. python scripts/send_summary_email.py")
        return

    sender = "manderson240@gmail.com"
    recipient = "manderson240@gmail.com"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Cohezion — Anthropic Application Package Ready"
    msg["From"] = sender
    msg["To"] = recipient

    # Read the handoff summary
    summary_path = Path(__file__).parent.parent / "docs" / "application" / "HANDOFF_SUMMARY.md"
    summary = summary_path.read_text() if summary_path.exists() else "Summary file not found."

    text_body = f"""Cohezion — Anthropic Application Package Ready
=============================================

LIVE LINKS
----------
Dashboard:  https://frameworkdesktop.tail54eb71.ts.net/
Genesis:    https://frameworkdesktop.tail54eb71.ts.net/genesis
Portfolio:  https://frameworkdesktop.tail54eb71.ts.net/portfolio
GitHub:     https://github.com/manderson240/cohezion

APPLY HERE: https://job-boards.greenhouse.io/anthropic/jobs/5061517008

APPLICATION MATERIALS (in repo at docs/application/):
- resume.md — 2-page resume mapped to Universes JD
- cover-letter.md — 1 page, direct technical tone
- technical-summary.md — 2-page FLUME overview
- interview-prep.md — walkthrough, answers, questions

DEMO (3 commands):
  cd demo
  uv run python quickstart.py    # Train 50 episodes (67s)
  uv run python evaluate.py      # 6 metrics + radar chart
  uv run python export_dataset.py # DPO + RLHF data export

CONTINUE FROM ANOTHER MACHINE:
  See docs/application/MULTI_MACHINE_GUIDE.md

ACTION ITEMS:
1. Fill in Education section in resume.md
2. Submit application
3. Check cohezion.duckdns.org (will activate when DNS stabilizes)

---
Full summary below:

{summary}
"""

    html_body = """<html><body style="font-family: monospace; background: #0a0a09; color: #faf9f5; padding: 20px;">
<h1 style="color: #10b981;">Cohezion — Application Package Ready</h1>

<h2>Live Links</h2>
<table style="border-collapse: collapse;">
<tr><td style="padding: 4px 12px;">Dashboard</td><td><a href="https://frameworkdesktop.tail54eb71.ts.net/" style="color: #60a5fa;">https://frameworkdesktop.tail54eb71.ts.net/</a></td></tr>
<tr><td style="padding: 4px 12px;">Genesis Engine</td><td><a href="https://frameworkdesktop.tail54eb71.ts.net/genesis" style="color: #60a5fa;">https://frameworkdesktop.tail54eb71.ts.net/genesis</a></td></tr>
<tr><td style="padding: 4px 12px;">Portfolio</td><td><a href="https://frameworkdesktop.tail54eb71.ts.net/portfolio" style="color: #60a5fa;">https://frameworkdesktop.tail54eb71.ts.net/portfolio</a></td></tr>
<tr><td style="padding: 4px 12px;">GitHub</td><td><a href="https://github.com/manderson240/cohezion" style="color: #60a5fa;">https://github.com/manderson240/cohezion</a></td></tr>
</table>

<h2 style="color: #f59e0b;">Apply Here</h2>
<p><a href="https://job-boards.greenhouse.io/anthropic/jobs/5061517008" style="color: #f59e0b; font-size: 18px;">https://job-boards.greenhouse.io/anthropic/jobs/5061517008</a></p>

<h2>Application Materials</h2>
<ul>
<li><code>docs/application/resume.md</code> — 2-page resume (fill in Education)</li>
<li><code>docs/application/cover-letter.md</code> — 1 page cover letter</li>
<li><code>docs/application/technical-summary.md</code> — 2-page FLUME overview</li>
<li><code>docs/application/interview-prep.md</code> — code walkthrough + answers</li>
</ul>

<h2>3-Command Demo</h2>
<pre style="background: #1a1a1a; padding: 12px; border-radius: 8px;">
cd demo
uv run python quickstart.py      # Train 50 episodes (67s)
uv run python evaluate.py        # 6 metrics + radar chart
uv run python export_dataset.py  # DPO + RLHF data export
</pre>

<h2>Continue From Another Machine</h2>
<pre style="background: #1a1a1a; padding: 12px; border-radius: 8px;">
git clone git@github.com:manderson240/cohezion.git
cd cohezion
uv venv && source .venv/bin/activate
uv pip install -e .
uv run python demo/quickstart.py
</pre>
<p>Full guide: <code>docs/application/MULTI_MACHINE_GUIDE.md</code></p>

<h2>Action Items</h2>
<ol>
<li>Fill in Education in <code>resume.md</code></li>
<li>Submit application</li>
<li>Check <code>cohezion.duckdns.org</code> — will go live when Duck DNS stabilizes</li>
</ol>

<hr style="border-color: #333;">
<p style="color: #666; font-size: 12px;">Generated by Cohezion Compound Engineering Session — 2026-03-29</p>
</body></html>"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"Email sent to {recipient}")


if __name__ == "__main__":
    main()
