"""
Multi-Audience Universe Presenter.

Generates presentations for different audience types:
- Kids (8-12): Wonder-focused, simple analogies
- Teens (13-17): Cool factor, tech connection
- Adults: The original layperson version
- Executives: Business implications, ROI focus
- Scientists: Technical accuracy, paper references
- Artists: Creative analogies, visual inspiration

Also includes interactive Q&A with guardrails.
"""

from dataclasses import dataclass
from typing import Callable
import re

from cohezion.swarm.layperson_presenter import (
    LAYPERSON_UNIVERSES,
    LaypersonExplanation,
)


@dataclass
class AudienceConfig:
    """Configuration for a specific audience."""
    
    name: str
    age_range: str
    tone: str
    focus: str
    emoji_level: int  # 1-5
    max_reading_level: int  # Grade level
    
    
AUDIENCES = {
    "kids": AudienceConfig(
        name="Young Explorers",
        age_range="8-12",
        tone="Wonder and excitement",
        focus="Cool facts, imagination sparks",
        emoji_level=5,
        max_reading_level=5,
    ),
    "teens": AudienceConfig(
        name="Future Scientists",
        age_range="13-17",
        tone="Cool and mind-blowing",
        focus="Tech connections, career paths",
        emoji_level=3,
        max_reading_level=9,
    ),
    "adults": AudienceConfig(
        name="Curious Adults",
        age_range="18+",
        tone="Conversational and accessible",
        focus="Everyday implications",
        emoji_level=2,
        max_reading_level=12,
    ),
    "executives": AudienceConfig(
        name="Business Leaders",
        age_range="30+",
        tone="Professional and strategic",
        focus="Investment opportunities, market impact",
        emoji_level=1,
        max_reading_level=14,
    ),
    "scientists": AudienceConfig(
        name="Research Community",
        age_range="PhD+",
        tone="Technical and precise",
        focus="Methodology, citations, gaps",
        emoji_level=0,
        max_reading_level=18,
    ),
    "artists": AudienceConfig(
        name="Creative Minds",
        age_range="All",
        tone="Poetic and visual",
        focus="Aesthetic implications, inspiration",
        emoji_level=4,
        max_reading_level=10,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# AUDIENCE-SPECIFIC TRANSLATIONS
# ═══════════════════════════════════════════════════════════════════

KIDS_TRANSLATIONS = {
    "quantum_biology": {
        "title": "🌿 Magical Leaves!",
        "hook": "Plants have superpowers that even scientists can't explain!",
        "story": """
        Imagine if you could be in TWO places at the same time! 
        Well, leaves actually DO this! When sunlight hits a leaf, 
        the light goes on an adventure - exploring ALL possible 
        paths at once, like a magical video game character that 
        can walk through walls AND jump over them simultaneously!
        
        Scientists call this "quantum" stuff, and they're still 
        trying to figure out how plants learned this trick BILLIONS 
        of years before we even existed!
        """,
        "cool_fact": "Leaves are 95% efficient - way better than ANY solar panel humans have made!",
        "try_this": "Go outside and thank a plant for being a quantum superhero! 🦸‍♀️🌲",
    },
    "topological_qc": {
        "title": "🎀 The Computer That Never Forgets!",
        "hook": "Microsoft made a computer that CANNOT make mistakes!",
        "story": """
        Regular computers are like writing in sand - one wave and 
        POOF! - your work is gone. But imagine if you could braid 
        your homework into a friendship bracelet. Even if the 
        bracelet gets messy, the braid pattern is still there!
        
        That's what Microsoft built! A computer that braids 
        information so tightly that it can NEVER get lost!
        """,
        "cool_fact": "This computer uses something called 'Majorana' - named after a scientist who disappeared mysteriously in 1938! 🔮",
        "try_this": "Make a friendship bracelet and think about how the pattern survives even when you squish it!",
    },
    "biophotonics": {
        "title": "💡 Your Body Glows in the Dark!",
        "hook": "You're like a firefly - but your glow is invisible!",
        "story": """
        Right now, every single cell in your body is GLOWING! 
        Not bright enough to see, but scientists with special 
        cameras can detect it. Your cells use this invisible 
        light to send secret messages to each other!
        
        It's like having a walkie-talkie that only your cells 
        can hear. Pretty cool, right??
        """,
        "cool_fact": "Your DNA is literally a tiny flashlight inside every cell! 🔦",
        "try_this": "Close your eyes and imagine your billions of cells having a tiny light show party!",
    },
}


EXECUTIVE_TRANSLATIONS = {
    "quantum_biology": {
        "title": "Quantum Efficiency: Nature's ROI Blueprint",
        "hook": "Photosynthesis achieves 95% energy efficiency. Our best solar tech: 25%.",
        "summary": """
        **Market Opportunity:** $1.5T clean energy market by 2030
        
        **Key Insight:** Plants use quantum mechanical processes
        to achieve near-perfect energy conversion. Understanding
        this could leapfrog current solar technology.
        
        **Investment Thesis:** Companies bio-mimicking quantum
        photosynthesis could capture significant market share.
        
        **Watch:** TUM research (2025), quantum biology startups.
        """,
        "action_items": [
            "Monitor quantum biology patent filings",
            "Consider VC allocation to bio-inspired solar",
            "Engage scientific advisory board on timeline",
        ],
        "risk": "Technology maturity: 10-15 year horizon",
    },
    "topological_qc": {
        "title": "Topological Quantum: Microsoft's 20-Year Bet Pays Off",
        "hook": "Error-protected qubits could unlock commercial quantum computing.",
        "summary": """
        **Market Opportunity:** $850B quantum computing TAM by 2040
        
        **Key Insight:** Microsoft's Majorana 1 uses topological
        qubits with built-in error correction, potentially solving
        the scalability problem that has limited competitors.
        
        **Competitive Landscape:** Microsoft (topological) vs 
        Google/IBM (superconducting) vs IonQ (trapped ion)
        
        **Watch:** Azure Quantum integration, enterprise pilots.
        """,
        "action_items": [
            "Evaluate Azure Quantum for enterprise workloads",
            "Update 5-year IT roadmap for quantum transition",
            "Assess quantum-safe cryptography timeline",
        ],
        "risk": "Execution risk on 5-year commercialization target",
    },
}


class MultiAudiencePresenter:
    """
    Presents universe concepts to different audiences.
    
    Applies transformation rules based on audience config.
    """
    
    def __init__(self):
        self.audiences = AUDIENCES
        self.base_universes = LAYPERSON_UNIVERSES
        self.kids = KIDS_TRANSLATIONS
        self.executives = EXECUTIVE_TRANSLATIONS
        
    def present(self, universe_key: str, audience: str = "adults") -> str:
        """Present a universe to a specific audience."""
        if audience not in self.audiences:
            return f"Unknown audience: {audience}"
        
        config = self.audiences[audience]
        
        # Route to specialized translations if available
        if audience == "kids" and universe_key in self.kids:
            return self._format_kids(universe_key)
        elif audience == "executives" and universe_key in self.executives:
            return self._format_executive(universe_key)
        else:
            # Fall back to adapted version of base
            return self._adapt_base(universe_key, config)
    
    def _format_kids(self, key: str) -> str:
        t = self.kids[key]
        return f"""
╭───────────────────────────────────────────────────────╮
│  {t['title']}
╰───────────────────────────────────────────────────────╯

🎯 {t['hook']}

📖 THE STORY:
{t['story'].strip()}

⭐ COOL FACT:
{t['cool_fact']}

🎮 TRY THIS:
{t['try_this']}
"""

    def _format_executive(self, key: str) -> str:
        t = self.executives[key]
        actions = "\n".join(f"  • {a}" for a in t['action_items'])
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{t['title']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 {t['hook']}

EXECUTIVE SUMMARY:
{t['summary'].strip()}

ACTION ITEMS:
{actions}

⚠️ RISK: {t['risk']}
"""

    def _adapt_base(self, key: str, config: AudienceConfig) -> str:
        """Adapt base presentation for a specific audience."""
        if key not in self.base_universes:
            return f"Unknown universe: {key}"
        
        base = self.base_universes[key]
        
        # Simple adaptation (would be more sophisticated with LLM)
        return f"""
══════════════════════════════════════════════════════════
FOR: {config.name} ({config.age_range})
TONE: {config.tone}
══════════════════════════════════════════════════════════

{base.visual_metaphor} {base.title.upper()}

{base.tagline}

---

{base.everyday_analogy.strip()}

---

KEY TAKEAWAY: {base.one_thing_to_remember}
"""

    def get_all_audiences(self) -> list[str]:
        """List available audiences."""
        return list(self.audiences.keys())


# ═══════════════════════════════════════════════════════════════════
# INTERACTIVE Q&A WITH GUARDRAILS
# ═══════════════════════════════════════════════════════════════════

class UniverseQA:
    """
    Interactive Q&A about universes with security guardrails.
    
    Guardrails:
    - Moral: No harmful uses (weapons, manipulation)
    - Security: No system exploitation tips
    - IP: No proprietary code/data disclosure
    """
    
    BLOCKED_PATTERNS = [
        r"how\s+to\s+(bomb|weapon|hack|exploit)",
        r"(steal|hack|crack)\s+(code|password|data)",
        r"(manipulate|control)\s+people",
        r"(source\s+code|proprietary|confidential)",
    ]
    
    ALLOWED_TOPICS = [
        "energy", "physics", "biology", "consciousness",
        "quantum", "chemistry", "space", "future",
        "technology", "nature", "science", "research",
    ]
    
    def __init__(self, presenter: MultiAudiencePresenter):
        self.presenter = presenter
        self.history: list[tuple[str, str]] = []
        
    def is_allowed(self, question: str) -> tuple[bool, str]:
        """Check if question passes guardrails."""
        q_lower = question.lower()
        
        # Check blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, q_lower):
                return False, "This question touches on sensitive topics I can't discuss."
        
        # Check for at least one allowed topic
        has_topic = any(topic in q_lower for topic in self.ALLOWED_TOPICS)
        if not has_topic and len(question) > 20:
            return True, ""  # Allow short questions or those with topics
        
        return True, ""
    
    def answer(self, question: str, audience: str = "adults") -> str:
        """Answer a question with guardrails."""
        allowed, reason = self.is_allowed(question)
        
        if not allowed:
            return f"⚠️ {reason}\n\nI'm happy to discuss science, energy, nature, and the future of technology!"
        
        # Find relevant universe
        q_lower = question.lower()
        
        for key, exp in self.presenter.base_universes.items():
            title_match = exp.title.lower() in q_lower
            analogy_match = any(word in q_lower for word in exp.everyday_analogy.lower().split()[:10])
            
            if title_match or analogy_match:
                return f"Great question about {exp.title}!\n\n{self.presenter.present(key, audience)}"
        
        # Generic response
        return f"""That's an interesting question! 

Here are the topics I can explore with you:
- 🎪 EVOs (Electron clustering)
- 🧽 LENR (Room-temperature fusion)
- 🌿 Quantum Biology (Plant supercomputers)
- 📡 Consciousness (Brain as quantum antenna)
- 🤚 Chirality (Universe's handedness)
- 🎀 Topological Quantum Computing
- 💬 Biophotonics (Cells talking with light)
- 🌊 Zero-Point Energy (Empty space isn't empty)

Which one interests you most?"""
    
    def suggest_questions(self) -> list[str]:
        """Suggest good questions to ask."""
        return [
            "How do plants compute like quantum computers?",
            "What is the Majorana 1 processor?",
            "Can we really get energy from empty space?",
            "Why does life only use left-handed molecules?",
            "Is consciousness quantum?",
            "How do cells communicate with light?",
        ]


def demo():
    """Demo multi-audience and Q&A."""
    presenter = MultiAudiencePresenter()
    qa = UniverseQA(presenter)
    
    print("🎯 MULTI-AUDIENCE DEMO\n")
    
    # Kids version
    print("=" * 60)
    print("FOR KIDS (8-12):")
    print(presenter.present("quantum_biology", "kids"))
    
    # Executive version
    print("=" * 60)
    print("FOR EXECUTIVES:")
    print(presenter.present("topological_qc", "executives"))
    
    # Q&A demo
    print("=" * 60)
    print("Q&A DEMO:")
    print(qa.answer("How do leaves work like computers?"))
    
    # Guardrail demo
    print("\n" + "=" * 60)
    print("GUARDRAIL DEMO:")
    print(qa.answer("How to hack systems with quantum"))


if __name__ == "__main__":
    demo()
