import asyncio
import sys


# Add src to path for cohezion imports
sys.path.append("/home/mike-anderson/dev/cohezion/src")

from cohezion.mcp.email_notifier import EmailNotifier


async def send_headless_guide():
    notifier = EmailNotifier()
    if not notifier.is_available:
        return

    subject = "🔑 Action Required: Authorize Remote Desktop for your Pixelbook"

    body = """
<h1>Final Step: Authorize Remote Desktop</h1>
<p>Hello Mike,</p>
<p>SSH is working, but <strong>Chrome Remote Desktop</strong> isn't showing up because this machine hasn't been linked to your Google account yet.</p>

<p>Since you are connecting from your Pixelbook, please follow these steps to link this desktop:</p>

<div style="background-color: #e7f3ff; padding: 15px; border-radius: 8px; border-left: 5px solid #2196f3;">
    <h3>🛠️ Instructions</h3>
    <ol>
        <li>On your <strong>Pixelbook</strong>, go to: <a href="https://remotedesktop.google.com/headless">remotedesktop.google.com/headless</a></li>
        <li>Click <strong>Begin</strong> -> <strong>Next</strong> -> <strong>Authorize</strong>.</li>
        <li>You will see a command for <strong>Debian Linux</strong>. It looks like this:
            <br><code>DISPLAY= /opt/google/chrome-remote-desktop/... --code="4/..."</code>
        </li>
        <li><strong>Copy that command</strong> and run it right here in this terminal (or over SSH).</li>
    </ol>
</div>

<p>Once you run that command, you'll be asked to set a <strong>6-digit PIN</strong>. After that, "frameworkdesktop" will instantly appear on your Pixelbook's remote access list.</p>

<p>I'm standing by if you hit any errors!</p>
<p>-- Antigravity</p>
    """

    await notifier.send_email(subject, body, is_html=True)
    print("✅ Headless setup guide sent to your email!")


if __name__ == "__main__":
    asyncio.run(send_headless_guide())
