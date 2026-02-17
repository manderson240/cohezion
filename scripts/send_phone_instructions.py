import asyncio

from cohezion.mcp.email_notifier import EmailNotifier


async def main():
    notifier = EmailNotifier()

    subject = "📱 Cohezion Remote Command Guide"
    body = """
<h2>How to Control your Swarm via Phone</h2>
<p>You can now send commands to the Cohezion swarm by replying to any alert or sending a new email with the subject starting with <b>[CMD]</b>.</p>

<h3>Available Commands</h3>
<ul>
    <li><b>[CMD] status</b>: Returns active Python/Ollama processes and SurrealDB health.</li>
    <li><b>[CMD] report</b>: Sends the latest autonomous research report.</li>
    <li><b>[CMD] ping</b>: Simple health check (returns PONG).</li>
    <li><b>[CMD] run [script_name]</b>: Starts a script in the <i>scripts/</i> directory (e.g., <code>[CMD] run mining_sprint</code>).</li>
    <li><b>[CMD] resume</b>: Clears resource throttles and signals agents to re-evaluate trajectories.</li>
</ul>

<h3>Proactive Alerts</h3>
<p>The swarm will automatically email you if:
<ul>
    <li>An agent is <b>Blocked</b> on user input.</li>
    <li>A <b>Security Block</b> (PromptGuard) is triggered.</li>
    <li><b>Resource Limits</b> are hit (GPU/Memory exhaustion).</li>
</ul>
</p>

<p><i>- Your Cohezion Swarm</i></p>
"""
    if notifier.is_available:
        await notifier.send_email(subject, body, is_html=True)
        print("Instruction email sent.")


if __name__ == "__main__":
    asyncio.run(main())
