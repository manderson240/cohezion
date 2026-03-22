import asyncio
import sys


# Add src to path for cohezion imports
sys.path.append("/home/mike-anderson/dev/cohezion/src")

from cohezion.mcp.email_notifier import EmailNotifier


async def send_final_guide():
    notifier = EmailNotifier()
    if not notifier.is_available:
        print("Error: Email notifier not available.")
        return

    subject = "🐧 Final Connection Guide: Linux-Native (Crostini) Access"

    # Connection details
    tailscale_ip = "100.125.138.97"
    username = "mike-anderson"

    body = f"""
<h1>Linux-Native Connection Guide (Crostini)</h1>
<p>Hello Mike,</p>
<p>Here are the definitive connection strings for your Pixelbook's Linux environment.</p>

<div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #333;">
    <h3>🌐 Host Info</h3>
    <ul>
        <li><strong>Tailscale IP:</strong> <code>{tailscale_ip}</code></li>
        <li><strong>User:</strong> <code>{username}</code></li>
    </ul>
</div>

<div style="margin-top: 20px;">
    <h3>💻 1. SSH (Terminal)</h3>
    <pre style="background-color: #2b2b2b; color: #f8f8f2; padding: 10px; border-radius: 5px;">ssh {username}@{tailscale_ip}</pre>
</div>

<div style="margin-top: 20px;">
    <h3>🖼️ 2. Remmina (Native GUI)</h3>
    <p>Run this to open the GUI client directly:</p>
    <pre style="background-color: #2b2b2b; color: #f8f8f2; padding: 10px; border-radius: 5px;">remmina -c rdp://{username}@{tailscale_ip}</pre>
    <p><em>Note: If prompted, select "High Color (16bpp)" for best performance.</em></p>
</div>

<div style="margin-top: 20px;">
    <h3>🚀 3. Xfreerdp (Pro CLI - Best Scaling)</h3>
    <p>This command matches your Pixelbook's resolution and goes full-screen automatically:</p>
    <pre style="background-color: #2b2b2b; color: #f8f8f2; padding: 10px; border-radius: 5px;">xfreerdp /v:{tailscale_ip} /u:{username} /dynamic-resolution /f</pre>
</div>

<div style="margin-top: 20px; background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107;">
    <h3>⚠️ Critical Step (On Framework Desktop)</h3>
    <p>For the RDP (GUI) options to work, you must enable this setting on your physical desktop:</p>
    <p><strong>Settings -> System -> Remote Desktop -> Enable "Desktop Sharing"</strong></p>
</div>

<p>I've also saved your display toggle script at <code>~/dev/cohezion/toggle_display.sh</code> if you need to manually force the resolution later.</p>
<p>Enjoy the native experience!<br>-- Antigravity</p>
    """

    success = await notifier.send_email(subject, body, is_html=True)
    if success:
        print("✅ Linux-native connection guide sent successfully!")
    else:
        print("❌ Failed to send final guide.")


if __name__ == "__main__":
    asyncio.run(send_final_guide())
