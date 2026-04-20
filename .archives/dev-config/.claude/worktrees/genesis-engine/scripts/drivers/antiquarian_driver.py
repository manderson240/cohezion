import asyncio
import logging

# Path injection
import sys
from datetime import datetime
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent.parent))

from cohezion.engineering.antiquarian import CodeAntiquarian


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/antiquarian.log"), logging.StreamHandler()],
)
logger = logging.getLogger("AntiquarianDriver")


async def main():
    logger.info("🏺 Code Antiquarian Driver: Online.")

    antiquarian = CodeAntiquarian()

    # Ensure handoff dir exists
    handoff_dir = Path("research/handoffs/antiquarian")
    handoff_dir.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            logger.info("🦴 Commencing new excavation cycle...")
            results = antiquarian.scan()

            if results:
                report = antiquarian.generate_markdown_report(results)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = handoff_dir / f"debt_report_{timestamp}.md"
                report_path.write_text(report)
                logger.info(f"📦 Handoff packet created: {report_path}")
            else:
                logger.info("✨ No debt found in this sector.")

        except Exception as e:
            logger.error(f"Excavation failed: {e}", exc_info=True)

        # Low frequency - once every 12 hours
        # In this demo state, let's keep it faster for verification (1 hour)
        logger.info("⌛ Sleeping for 1 hour (Low frequency mode)...")
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
