import logging
import math
from cohezion.swarm.agents.gaia_agent import GaiaAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.seti.array import get_exogenic_array, Signal
from cohezion.bio.biophotonics import Wavelength

logger = logging.getLogger(__name__)

class SETIAgent(GaiaAgent):
    """
    SETI Agent (Phase 19).

    Gateway 30: Exogenic Signal Processing.

    Role:
    - Listener: Scans ExogenicArray for anomalies.
    - Ambassador: Decodes Arecibo-style bitmaps.
    """
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.array = get_exogenic_array()
        self.id = "SETIAgent"

    async def process(self, query: str) -> str:
        """
        Listen for signals and decode anomalies.
        """
        report = f"\n\n### 👽 SETI Report (Exogenic Scan)\n"

        # 1. Active Scanning (Mockup: usually would scan recent vector buffer)
        # For simulation, we check if the query ITSELF contains a hidden signal

        # Arecibo Check: Is there a binary string hidden in the query?
        # Extract potential binary sequences (length > 10)
        import re
        binary_candidates = re.findall(r'[01]{10,}', query.replace(" ", ""))

        for candidate in binary_candidates:
             signal = self.array.analyze_bitmap(candidate)
             if signal:
                 dims = signal.payload.split(": ")[1] # e.g. "23x73"
                 decoded = self._render_bitmap(candidate, dims)
                 self._emit(Wavelength.UV, 1.0, "FIRST CONTACT PROTOCOL INITIATED")

                 report += f"🚨 **TECHNOSIGNATURE DETECTED** 🚨\n"
                 report += f"Type: {signal.signature_type}\n"
                 report += f"Payload: {signal.payload}\n"
                 report += f"**Decoded Bitmap**:\n{decoded}\n"

                 return report # Return immediately for high priority interrupt

        # 2. General Anomaly Scan
        # In a real run we'd pass actual vectors.
        # Here we report nominal unless triggered.
        report += "Status: Nominal (Background Noise Only).\n"

        return await super().process(query) + report

    def _render_bitmap(self, binary: str, dims_str: str) -> str:
        """
        Visualizes the binary string as a grid.
        dims_str format: "RxC"
        """
        try:
            r, c = map(int, dims_str.split("x"))
            # Heuristic: Arecibo standard is usually Rows x Cols, but we might need to swap
            # We try the order provided

            grid = ""
            for i in range(r):
                row = binary[i*c : (i+1)*c]
                # Replace 0 with space, 1 with block for visibility
                line = row.replace("0", "░").replace("1", "█")
                grid += line + "\n"
            return f"```\n{grid}```"
        except Exception as e:
            return f"Decoding Error: {e}"

    async def close(self):
        await super().close()
