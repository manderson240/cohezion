
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

from cohezion.db.admin import DBAdmin
from cohezion.reliability.monitor import get_resource_monitor
# We will use BaseAgent's LLM capability via a specialized subclass or direct mixin later
# For now, simplistic LLM call via Ollama direct to avoid circular imports if possible,
# OR strictly import BaseAgent inside methods.

logger = logging.getLogger(__name__)

class ReflexAgent:
    """
    The 'Subconscious' Reflex System.
    
    Monitors system_pulse for stress events (anomalies).
    When system is calm, it reflects on past stress and generates insights.
    
    SAFEGUARDS:
    - Never runs if Current CPU > 80%
    - Never runs if Current RAM > 80%
    - Never runs if VRAM > 85%
    """
    
    def __init__(self):
        self.dba = DBAdmin()
        self.monitor = get_resource_monitor()
        self.insights_dir = Path("src/cohezion/knowledge_graph/auto_generated")
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    async def _safe_to_run(self) -> bool:
        """Check if system has capacity for reflection."""
        vitals = self.monitor.get_vitals()
        if (vitals['cpu_percent'] > 80 or 
            vitals['memory_percent'] > 80 or 
            vitals.get('vram_percent', 0) > 85):
            logger.warning(f"Reflex aborted due to high load: {vitals}")
            return False
        return True

    def _check_rate_limit(self) -> bool:
        """Limit insight generation to 5 per day to prevent spam."""
        today = datetime.now().strftime("%Y-%m-%d")
        todays_insights = list(self.insights_dir.glob(f"INSIGHT_{today}*.md"))
        
        if len(todays_insights) >= 5:
            logger.warning(f"🛑 Reflex Rate Limit Reached ({len(todays_insights)}/5 today). Skipping.")
            return False
        return True

    async def scan_and_reflect(self):
        """Main entry point."""
        if not await self._safe_to_run():
            return
            
        if not self._check_rate_limit():
            return
            
        await self.dba.connect()
        try:
            # 1. Find recent unanalyzed stress events
            # Logic: Look for dilation < 0.5 in last hour? 
            # For prototype, we just query for any record with dilation < 0.1 
            # that hasn't been flagged (we'd need a flag field). 
            # For now, let's just look at the last 10 records and see if any are 'bad'.
            
            query = "SELECT * FROM system_pulse ORDER BY timestamp DESC LIMIT 20;"
            response = await self.dba.client.query(query)
            
            rows = []
            if isinstance(response, list) and len(response) > 0:
                 if 'result' in response[0]:
                     rows = response[0]['result']
                 else:
                     rows = response
            
            if not rows:
                return

            stress_events = [r for r in rows if r.get('dilation_factor', 1.0) < 0.5]
            
            if stress_events:
                logger.info(f"Reflex found {len(stress_events)} recent stress events.")
                # Aggregate context
                event = stress_events[0] # Analyze the most recent one
                timestamp = event.get('timestamp', 'unknown')
                
                # Check if insight already exists for this timestamp (deduplication)
                # Sanitize timestamp for filename
                safe_ts = str(timestamp).replace(' ', '_').replace(':', '').replace('.', '').replace('+', '')
                insight_file = self.insights_dir / f"INSIGHT_{safe_ts}.md"
                
                if insight_file.exists():
                    logger.info("Insight already exists. Skipping.")
                    return

                # GENERATE INSIGHT
                # We use a lightweight LLM call here.
                # To avoid complex imports, we'll use a local helper request or BaseAgent if we can.
                await self._generate_insight(event, insight_file)
                
        except Exception as e:
            logger.error(f"Reflex cycle failed: {e}")
        finally:
            await self.dba.close()

    async def _generate_insight(self, event_data: dict, output_file: Path):
        """Asks LLM to analyze the stress data."""
        import requests
        
        prompt = f"""
        SYSTEM METRICS ANALYSIS
        
        The Cohezion System experienced a stress event.
        Timestamp: {event_data.get('timestamp')}
        Dilation Factor: {event_data.get('dilation_factor')} (1.0 = Healthy, <0.1 = Frozen)
        Hardware: {json.dumps(event_data.get('hardware', {}))}
        Software: {json.dumps(event_data.get('software', {}))}
        
        Provide a brief (3 bullet points) retrospective on why this might have happened and 1 recommendation.
        """
        
        try:
            # Direct Ollama call to avoid loop/dependency hell for this background process
            # Use a smaller model for speed/memory if possible, e.g. phi4 or mistral
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi3:mini", # Fast, relatively smart (3.8B)
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                content = response.json()['response']
                md = f"# INSIGHT: System Stress Analysis\n\n**Date**: {datetime.now()}\n\n## Trigger\nDilation Factor: {event_data.get('dilation_factor')}\n\n## Analysis\n{content}\n"
                output_file.write_text(md)
                logger.info(f"📝 Insight written to {output_file}")
            else:
                logger.error(f"Ollama failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Insight Generation failed: {e}")

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        agent = ReflexAgent()
        await agent.scan_and_reflect()
    
    asyncio.run(main())
