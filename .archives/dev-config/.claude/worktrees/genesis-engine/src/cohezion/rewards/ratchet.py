import logging
from cohezion.universe.triune_manifold import TriuneState
from cohezion.persistence.obsidian_mcp import ObsidianMemoryMCP

logger = logging.getLogger(__name__)

class RatchetMechanism:
    """
    Identifies and locks high-performing agent states into the Root of Trust.
    """
    
    def __init__(
        self,
        obsidian_mcp: ObsidianMemoryMCP,
        threshold: float = 0.85
    ):
        """
        Initializes the ratchet mechanism.
        
        Args:
            obsidian_mcp: Client for visual/semantic persistence.
            threshold: The score threshold required to trigger a ratchet.
        """
        self.obsidian_mcp = obsidian_mcp
        self.threshold = threshold

    async def evaluate_and_ratchet(
        self,
        trajectory_id: str,
        state: TriuneState,
        score: float,
        coherence: float
    ) -> bool:
        """
        Checks if the current performance warrants a ratchet event.
        
        If score >= threshold, persists a permanent record to the Root of Trust.
        
        Returns:
            bool: True if a ratchet event occurred.
        """
        if score < self.threshold:
            logger.debug(f"Score {score:.4f} below threshold {self.threshold}. No ratchet.")
            return False
            
        logger.info(f"🚀 RATCHET TRIGGERED: Score {score:.4f} exceeds threshold!")
        
        ratchet_id = f"ratchet_{trajectory_id}"
        
        # Persist to Obsidian as a permanent 'Success' anchor
        await self.obsidian_mcp.store_state_summary(
            trajectory_id=ratchet_id,
            state=state,
            coherence=coherence
        )
        
        return True
