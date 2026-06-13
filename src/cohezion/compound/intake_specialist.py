"""Token-efficient intake specialist agent - greet, parse, and hand off requests.

The intake specialist sits before Step 1 of the CompoundExecutor pipeline:

User Request
    ↓
IntakeSpecialist.greet() → Warm cache, establish session
    ↓
IntakeSpecialist.process_request() → Parse NL → AgentTask (0 tokens via cache)
    ↓
CompoundExecutor.execute_task() → Existing 7-step pipeline
    ↓
IntakeSpecialist.log_success() → Cache pattern for future

Token efficiency target: <10 tokens/request average (95% cache hit) vs. 200-350 baseline.

Example:
    ```python
    intake = IntakeSpecialist(mcp_client, token_client)

    # Greet and establish session
    greeting = await intake.greet(user_id="user123")
    print(f"Session: {greeting.session_id}, cached {greeting.cache_entries} patterns")

    # Process request
    task = await intake.process_request("Generate 10 story ideas")
    print(f"Task: {task.operation_type}, skills: {task.available_skills}")

    # Repeat request (cache hit)
    task2 = await intake.process_request("Generate 10 story ideas")
    assert task.task_id == task2.task_id  # Same from cache

    # Log success to cache
    intake.log_success("Generate 10 story ideas", task)
    ```
"""

import logging
import uuid
from dataclasses import dataclass

from cohezion.compound.intent_classifier import IntentClassifier
from cohezion.compound.prompt_optimizer import PromptOptimizer
from cohezion.compound.request_cache import RequestCache
from cohezion.compound.skill_selector import SkillSelector
from cohezion.compound.team_executor import AgentTask
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class IntakeGreeting:
    """Response from greet() - session context and warm cache status."""

    session_id: str  # Unique session identifier
    cache_entries: int  # Number of patterns loaded from vault
    cache_warmed: bool  # Whether cache warm-up succeeded
    user_id: str = ""  # User identifier


class IntakeSpecialist:
    """Token-efficient intake specialist - greet, parse, hand off requests.

    Minimizes token usage through aggressive caching and heuristics:
    - L1: Exact hash matching (0 tokens, <1ms)
    - L2: Semantic similarity (0 tokens, ~5ms)
    - Heuristics: Keyword classification (0 tokens)
    - Vault: Experience-guided skill selection (0 LLM tokens, 5-10ms)

    Example:
        ```python
        intake = IntakeSpecialist(mcp_client)
        greeting = await intake.greet(user_id="user123")
        task = await intake.process_request("Generate ideas")
        intake.log_success("Generate ideas", task)
        ```
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        token_client: object | None = None,
        project: str = "cohezion",
    ):
        """Initialize intake specialist.

        Args:
            mcp_client: Connected MCPClient for vault operations
            token_client: Optional token client (unused for caching)
            project: Project name for vault queries
        """
        self.mcp_client = mcp_client
        self.token_client = token_client
        self.project = project

        # Initialize components
        self.classifier = IntentClassifier(default_operation="generate")
        self.optimizer = PromptOptimizer(enable_filler_removal=True, estimate_tokens=True)
        self.cache = RequestCache(mcp_client, l1_size=256, l2_size=512)
        self.skill_selector = SkillSelector(mcp_client)

        # Session tracking
        self.session_id: str | None = None
        self.user_id: str | None = None
        self.greeting: IntakeGreeting | None = None

    async def greet(self, user_id: str, initial_request: str = "") -> IntakeGreeting:
        """Greet user and warm cache from vault.

        Establishes a session and loads cached patterns from vault to prime
        L1 and L2 caches for future requests.

        Args:
            user_id: Identifier for the user/session
            initial_request: Optional first request (not processed, for context)

        Returns:
            IntakeGreeting with session_id and cache status
        """
        # Generate session ID
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id

        logger.info(f"Greeting user {user_id} (session {self.session_id[:8]}...), warming cache...")

        # Warm cache from vault
        cache_entries = await self._warm_cache_from_vault()

        # Create greeting response
        self.greeting = IntakeGreeting(
            session_id=self.session_id,
            cache_entries=cache_entries,
            cache_warmed=cache_entries > 0,
            user_id=user_id,
        )

        logger.info(
            f"Session ready: {self.session_id[:8]}... (cache warmed with {cache_entries} patterns)"
        )

        return self.greeting

    async def process_request(self, request_text: str) -> AgentTask:
        """Parse natural language request → AgentTask (0 tokens via cache).

        Implements a 4-tier strategy:
        1. L1 cache: Exact hash match (0 tokens, <1ms)
        2. L2 cache: Semantic similarity (0 tokens, ~5ms)
        3. Heuristics: Keyword classification (0 tokens)
        4. Vault query: Experience-guided skills (0 LLM tokens, 5-10ms)

        Args:
            request_text: User request in natural language

        Returns:
            AgentTask ready for CompoundExecutor
        """
        if not request_text or not isinstance(request_text, str):
            raise ValueError("request_text must be non-empty string")

        logger.debug(f"Processing request: {request_text[:100]}...")

        # Tier 1: L1 exact cache match (0 tokens, <1ms)
        cached_task = self.cache.get_exact(request_text)
        if cached_task:
            logger.debug(f"Tier 1 hit (exact match): {request_text[:50]}...")
            return cached_task

        # Tier 2: L2 semantic cache match (0 tokens, ~5ms)
        cached_task = self.cache.get_semantic(request_text, threshold=0.85)
        if cached_task:
            logger.debug(f"Tier 2 hit (semantic): {request_text[:50]}...")
            return cached_task

        # Tier 3: Heuristic processing (0 tokens)
        # Classify operation type via keyword matching
        operation_type = self.classifier.classify(request_text)
        logger.debug(f"Classified as: {operation_type}")

        # Optimize prompt for token efficiency
        optimized_text = self.optimizer.optimize(request_text)
        logger.debug(f"Optimized: {optimized_text[:50]}...")

        # Tier 4: Skill selection via vault (0 LLM tokens, 5-10ms)
        skills = self.skill_selector.select_skills(
            task_description=optimized_text,
            operation_type=operation_type,
            top_k=3,
        )

        available_skill_names = [s.skill_name for s in skills] if skills else []

        # Create AgentTask
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_id="intake-specialist",
            description=optimized_text,
            operation_type=operation_type,
            available_skills=available_skill_names,
            timeout_seconds=300.0,
        )

        logger.info(
            f"Created task: {task.task_id[:8]}... (op={operation_type}, skills={available_skill_names})"
        )

        return task

    def log_success(self, request_text: str, task: AgentTask) -> None:
        """Cache successful request → task mapping for future reuse.

        Called after task execution succeeds to cache the pattern for
        future requests.

        Args:
            request_text: Original user request
            task: Successfully executed AgentTask
        """
        try:
            self.cache.put(request_text, task)
            logger.info(f"Logged success: {request_text[:50]}... → {task.task_id[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to log success: {e}")

    def get_session_stats(self) -> dict:
        """Get statistics for current session.

        Returns:
            Dictionary with cache hit rates, request counts, token savings
        """
        cache_stats = self.cache.get_stats()

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "cache_stats": cache_stats,
        }

    async def _warm_cache_from_vault(self) -> int:
        """Warm cache by loading patterns from vault.

        Args:
            self: Instance context

        Returns:
            Number of patterns loaded
        """
        try:
            # Use RequestCache's warm_from_vault which handles vault queries
            count = self.cache.warm_from_vault(project=self.project, limit=100)
            return count
        except Exception as e:
            logger.warning(f"Failed to warm cache: {e}")
            return 0
