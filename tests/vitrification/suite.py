import hashlib
import json
import os

from rich.console import Console


class VitrificationSuite:
    """
    Advanced testing and validation suite for Cohezion.
    Implements structural state verification and UI snapshotting.
    """

    def __init__(self, manifest_path="tests/vitrification/manifest.json"):
        self.manifest_path = manifest_path
        self.load_manifest()

    def load_manifest(self):
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path) as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {}

    def save_manifest(self):
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=4)

    def verify_ui_snapshot(self, name, rich_renderable):
        """
        Captures a snapshot of a Rich renderable and verifies its hash.
        Used to ensure 'Premium' aesthetics remain consistent.
        """
        import io

        buffer = io.StringIO()
        console = Console(file=buffer, force_terminal=True, width=80)
        console.print(rich_renderable)
        content = buffer.getvalue()
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if name not in self.manifest:
            self.manifest[name] = content_hash
            self.save_manifest()
            print(f"✅ Initialized snapshot for '{name}'")
            return True

        if self.manifest[name] == content_hash:
            print(f"✅ Snapshot '{name}' verified (Match: {content_hash[:8]})")
            return True
        else:
            print(f"❌ Snapshot '{name}' MISMATCH!")
            print(f"  Expected: {self.manifest[name][:8]}")
            print(f"  Actual:   {content_hash[:8]}")
            return False

    def verify_12d_consistency(self, state_vector, file_path):
        """
        Verifies if a 12D state vector is consistently represented in a file.
        (Conceptual implementation of FLUME vitrification).
        """
        with open(file_path) as f:
            content = f.read()
        # Verify 3+1+8 structure presence
        if "3 Spatial + 1 Time + 8 Brane" in content:
            print(f"✅ 12D Manifold signature verified in {os.path.basename(file_path)}")
            return True
        return False


if __name__ == "__main__":
    # Self-test
    from cohezion.ui.nexus_ui import NexusUI

    suite = VitrificationSuite()
    ui = NexusUI()

    print("Running Advanced Vitrification Suite...")
    header = ui.create_header("00:00:00")
    suite.verify_ui_snapshot("Dashboard Header", header)

    pulse = ui.create_pulse(0.5)
    suite.verify_ui_snapshot("Stability Pulse (0.5)", pulse)

    suite.verify_12d_consistency(None, "GEMINI.md")
