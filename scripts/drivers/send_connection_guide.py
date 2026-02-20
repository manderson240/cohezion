import asyncio
import sys


# Add src to path for cohezion imports
sys.path.append("/home/mike-anderson/dev/cohezion/src")

from cohezion.mcp.email_notifier import EmailNotifier


async def send_guide():
    notifier = EmailNotifier()
    if not notifier.is_available:
        print("Error: Email notifier not available.")
        return

    subject = "🚀 Connection Guide: Remote Access to Framework Desktop"

    # Connection details
    tailscale_ip = "100.125.138.97"
    username = "mike-anderson"

    body = f"""
<h1>Remote Connection Guide</h1>
<p>Hello Mike,</p>
<p>Here are the directions to connect to this Framework Desktop from your Pixelbook.</p>

<div style="background-color: #f4f4f4; padding: 15px; border-radius: 8px; border-left: 5px solid #4ECDC4;">
    <h3>🌐 Connection Info</h3>
    <ul>
        <li><strong>Tailscale IP:</strong> <code>{tailscale_ip}</code></li>
        <li><strong>Username:</strong> <code>{username}</code></li>
    </ul>
</div>

<div style="margin-top: 20px;">
    <h3>🛠️ 1. SSH Access (Terminal)</h3>
    <p>On your Pixelbook, open the <strong>Terminal</strong> and run:</p>
    <pre style="background-color: #333; color: #fff; padding: 10px; border-radius: 5px;">ssh {username}@{tailscale_ip}</pre>
    <p><em>Note: If prompted about "host authenticity", type <strong>yes</strong>.</em></p>
</div>

<div style="margin-top: 20px;">
    <h3>🖥️ 2. Desktop Access (Chrome Remote Desktop)</h3>
    <p>1. Open Chrome on your Pixelbook.</p>
    <p>2. Go to: <a href="https://remotedesktop.google.com/access">remotedesktop.google.com/access</a></p>
    <p>3. You should see <strong>"frameworkdesktop"</strong> in the list. Click it to connect.</p>
</div>

<div style="margin-top: 20px; background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107;">
    <h3>⚠️ Required Cleanup (Run on Desktop)</h3>
    <p>I was unable to start the services due to sudo restrictions. Please run these commands on this desktop once to finalize the setup:</p>
    <pre style="background-color: #eee; padding: 10px; border-radius: 5px;">
sudo systemctl enable --now sshd
sudo systemctl enable --now chrome-remote-desktop
sudo ufw allow ssh
    </pre>
</div>

<p>Safe connecting!<br>-- Antigravity</p>
    """

    success = await notifier.send_email(subject, body, is_html=True)
    if success:
        print("✅ Connection guide sent successfully!")
    else:
        print("❌ Failed to send connection guide.")


if __name__ == "__main__":
    asyncio.run(send_guide())
