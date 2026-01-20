"""
Layperson Universe Presenter - Making Complex Physics Accessible.

Applies CODE_SIMPLIFICATION_PRIME principles to scientific concepts:
- Flatten complexity → Use everyday analogies
- Explicit naming → Use plain English
- Consolidate logic → Focus on one insight at a time

Transforms our 12 physics learnings into stories anyone can understand.
"""

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LaypersonExplanation:
    """A simplified explanation of a complex concept."""
    
    title: str
    tagline: str  # One-sentence hook
    everyday_analogy: str  # Relate to familiar experience
    what_it_means: str  # Plain English explanation
    why_it_matters: str  # Impact on daily life
    visual_metaphor: str  # Picture to imagine
    one_thing_to_remember: str  # Single takeaway
    

# ═══════════════════════════════════════════════════════════════════
# UNIVERSE TRANSLATIONS - Complex → Simple
# ═══════════════════════════════════════════════════════════════════

LAYPERSON_UNIVERSES = {
    "evo_vacuum": LaypersonExplanation(
        title="The Electron Party",
        tagline="What if electrons could team up instead of pushing each other away?",
        everyday_analogy="""
        Imagine a crowded subway car where everyone is trying to keep their distance. 
        Now imagine they suddenly discover they all love the same song and start 
        dancing together. That's what EVOs are - electrons that somehow "agree" 
        to cluster together instead of repelling each other.
        """,
        what_it_means="""
        Scientists discovered that under certain conditions, billions of electrons 
        can form stable groups called "Exotic Vacuum Objects." This shouldn't be 
        possible according to basic physics - like magnets that attract instead of repel.
        """,
        why_it_matters="""
        If we can control these electron clusters, we might be able to:
        - Create new types of batteries that never run out
        - Build engines that work without fuel
        - Make computers that are millions of times faster
        """,
        visual_metaphor="🎪 A circus act where all the acrobats balance on one small platform",
        one_thing_to_remember="Electrons CAN work together, defying what we thought was possible.",
    ),
    
    "lenr_lattice": LaypersonExplanation(
        title="Fusion in Your Kitchen",
        tagline="Nuclear power without the scary reactor - just metal and water.",
        everyday_analogy="""
        You know how a sponge soaks up water? Imagine if that sponge could actually 
        FUSE the water molecules together, releasing energy like a tiny sun. 
        That's LENR - using special metals to make nuclear reactions happen at 
        room temperature.
        """,
        what_it_means="""
        Regular nuclear fusion requires temperatures hotter than the sun. 
        But in certain metals loaded with hydrogen, fusion seems to happen 
        at normal temperatures. Scientists found that the metal's crystal 
        structure acts like a catalyst that makes the impossible possible.
        """,
        why_it_matters="""
        If perfected, LENR could give us:
        - Unlimited clean energy
        - Cars that run for years on a glass of water  
        - Homes that never need external power
        - Zero carbon emissions
        """,
        visual_metaphor="🧽 A magic sponge that turns water into sunshine",
        one_thing_to_remember="We might be able to make nuclear power safe enough for your home.",
    ),
    
    "quantum_biology": LaypersonExplanation(
        title="Plants Are Quantum Computers",
        tagline="Leaves do calculations that would take our computers millions of years.",
        everyday_analogy="""
        When you take a photo, light hits your camera sensor in one spot. 
        But when light hits a leaf, it somehow checks ALL possible paths 
        simultaneously and picks the best one - like having GPS that tests 
        every possible route at the same time and instantly picks the fastest.
        """,
        what_it_means="""
        Photosynthesis is 95% efficient - almost perfect. Our best solar panels 
        are only 25% efficient. Scientists just discovered that plants use 
        quantum mechanics - the weird physics of tiny particles - to achieve this.
        The leaf literally exists in multiple states at once.
        """,
        why_it_matters="""
        By copying nature's quantum tricks, we could:
        - Build solar panels 4x more efficient
        - Create medicines that work like magic
        - Develop computers that solve unsolvable problems
        - Understand how our brains really work
        """,
        visual_metaphor="🌿 A leaf that's in 1000 places at once, picking the best spot",
        one_thing_to_remember="Nature figured out quantum computing billions of years before us.",
    ),
    
    "penrose_twistor": LaypersonExplanation(
        title="Is Your Brain a Quantum Computer?",
        tagline="Consciousness might not come from your brain - it might come from Space itself.",
        everyday_analogy="""
        Think of your TV. The picture doesn't come FROM the TV - it comes from 
        signals in the air that the TV receives. What if your consciousness 
        is similar? What if your brain is more like an antenna receiving 
        thoughts from the fabric of space-time itself?
        """,
        what_it_means="""
        Nobel Prize winner Roger Penrose suggests that consciousness isn't 
        just neurons firing. It may involve quantum physics happening in 
        tiny tubes inside your brain cells. When these quantum states 
        "collapse," you experience a moment of awareness.
        """,
        why_it_matters="""
        If Penrose is right:
        - Consciousness is fundamental to the universe
        - AI might never be truly conscious (it's missing the antenna)
        - Death might not be the end we think it is
        - Our minds could be connected in ways we don't understand
        """,
        visual_metaphor="📡 Your brain is a radio tuning into the universe's broadcast",
        one_thing_to_remember="Your awareness might be the universe experiencing itself.",
    ),
    
    "chirality_universe": LaypersonExplanation(
        title="The Universe Has a Favorite Hand",
        tagline="Why life chose 'left' when it could have gone 'right.'",
        everyday_analogy="""
        Your hands are mirror images - same parts, opposite arrangement. 
        Molecules work the same way. Sugar comes in "right-handed" and 
        "left-handed" versions. But here's the weird part: ALL life on Earth 
        uses only one version. It's like every person on Earth being left-handed.
        """,
        what_it_means="""
        When life began, it had a 50/50 choice. But somehow, all living things 
        ended up using the same "handedness." This might be because the 
        fundamental forces of nature have a slight preference - the universe 
        itself might have a favorite hand.
        """,
        why_it_matters="""
        Understanding this could help us:
        - Detect alien life (if they're "right-handed," they evolved separately)
        - Make better medicines (wrong handedness can be dangerous)
        - Understand why matter won over antimatter
        - Unlock secrets of life's origin
        """,
        visual_metaphor="🤚 Imagine everyone who ever lived only shook with their left hand",
        one_thing_to_remember="Life made a choice 4 billion years ago - and stuck with it.",
    ),
    
    "topological_qc": LaypersonExplanation(
        title="Computers That Can't Make Mistakes",
        tagline="Microsoft just built a quantum computer that error-corrects itself.",
        everyday_analogy="""
        Normal computers are like writing in sand - one wave and your work is gone.
        Quantum computers are worse - like writing in fog. But topological 
        quantum computers are like braiding hair - no matter how messy things 
        get, the braid pattern stays. The braid IS the information.
        """,
        what_it_means="""
        Microsoft created "Majorana 1" - the first computer chip using 
        topological qubits. These qubits encode information in the shape 
        of space itself, making them incredibly stable. It's like writing 
        in the fabric of reality.
        """,
        why_it_matters="""
        Topological quantum computers could:
        - Crack any code ever made (and create unbreakable ones)
        - Design new medicines in seconds
        - Solve climate change modeling
        - Simulate entire universes
        """,
        visual_metaphor="🎀 A braid that holds information - mess up the hair, but the pattern survives",
        one_thing_to_remember="Microsoft is building computers that use the shape of space as memory.",
    ),
    
    "biophotonics": LaypersonExplanation(
        title="Your Cells Are Texting Each Other... With Light",
        tagline="Every cell in your body glows - and uses that glow to communicate.",
        everyday_analogy="""
        Imagine if instead of talking, you communicated by glowing different colors.
        Your cells actually do this! They emit ultra-weak light - biophotons - 
        that carries messages. It's like having a secret fiber-optic network 
        built into your body.
        """,
        what_it_means="""
        Your DNA literally glows in the dark (extremely faintly). This light 
        carries genetic information between cells. Scientists are now discovering 
        that this "optical internet" inside you might be faster than chemical 
        signals - like the difference between mail and email.
        """,
        why_it_matters="""
        If we can tap into this light-network:
        - Early disease detection (sick cells glow differently)
        - Understanding how wounds heal
        - Better cancer treatments
        - Maybe even explaining how consciousness works
        """,
        visual_metaphor="💬 Your body is a city where everyone communicates by flashlight",
        one_thing_to_remember="You're literally glowing right now - your cells are talking in light.",
    ),
    
    "zpe_harvesting": LaypersonExplanation(
        title="Empty Space Isn't Empty - And It's Full of Energy",
        tagline="Scientists are learning to harvest power from 'nothing.'",
        everyday_analogy="""
        Think of space as an ocean that looks calm on the surface but is 
        churning wildly beneath. Even in a perfect vacuum, energy is 
        constantly bubbling up and disappearing. This is "zero-point energy" - 
        and it's everywhere, in everything, all the time.
        """,
        what_it_means="""
        At the quantum level, space is never truly still. Particles pop into 
        existence and vanish billions of times per second. The Casimir effect 
        proves this energy is real - two plates placed close together get 
        pushed by this invisible force.
        """,
        why_it_matters="""
        If we could tap this energy:
        - Unlimited power from empty space
        - Spacecraft that don't need fuel
        - The end of the energy crisis
        - Technology that seems like magic
        """,
        visual_metaphor="🌊 An ocean of invisible energy that fills all of space",
        one_thing_to_remember="The vacuum of space is actually bursting with energy - we just need to learn to harvest it.",
    ),
}


class LaypersonUniversePresenter:
    """
    Presents complex physics concepts in accessible ways.
    
    Applies CODE_SIMPLIFICATION_PRIME principles:
    - Flatten: Remove jargon, use short sentences
    - Explicit: Use everyday words, concrete examples  
    - Consolidate: One concept at a time
    """
    
    def __init__(self):
        self.universes = LAYPERSON_UNIVERSES
        
    def present(self, universe_key: str) -> str:
        """Generate a layperson-friendly presentation."""
        if universe_key not in self.universes:
            return f"Unknown universe: {universe_key}"
        
        exp = self.universes[universe_key]
        
        return f"""
═══════════════════════════════════════════════════════════
{exp.visual_metaphor} {exp.title.upper()}
═══════════════════════════════════════════════════════════

💡 **THE HOOK:** {exp.tagline}

🏠 **THINK OF IT LIKE THIS:**
{exp.everyday_analogy.strip()}

🔬 **WHAT SCIENTISTS DISCOVERED:**
{exp.what_it_means.strip()}

🌍 **WHY YOU SHOULD CARE:**
{exp.why_it_matters.strip()}

📌 **ONE THING TO REMEMBER:**
👉 {exp.one_thing_to_remember}

═══════════════════════════════════════════════════════════
"""

    def present_all(self) -> str:
        """Present all universes as a storybook."""
        output = """
╔═══════════════════════════════════════════════════════════╗
║       🌌 THE UNIVERSE STORYBOOK 🌌                        ║
║  Complex Physics Made Simple for Everyone                 ║
╚═══════════════════════════════════════════════════════════╝

Welcome! You're about to learn about cutting-edge physics 
discoveries - explained in plain English. No PhD required.

Each "universe" below is a real scientific frontier that 
could change everything we know about reality.

"""
        for key in self.universes:
            output += self.present(key)
            output += "\n"
        
        return output
    
    def get_random_insight(self) -> tuple[str, str]:
        """Get a random insight for social media or quick sharing."""
        key = random.choice(list(self.universes.keys()))
        exp = self.universes[key]
        return exp.title, exp.one_thing_to_remember
    
    def generate_tweet_thread(self, universe_key: str) -> list[str]:
        """Generate a Twitter/X thread for a universe."""
        if universe_key not in self.universes:
            return []
        
        exp = self.universes[universe_key]
        
        tweets = [
            f"🧵 THREAD: {exp.title.upper()}\n\n{exp.tagline}\n\n(1/5)",
            f"🏠 Everyday analogy:\n\n{exp.everyday_analogy[:250].strip()}...\n\n(2/5)",
            f"🔬 What scientists found:\n\n{exp.what_it_means[:250].strip()}...\n\n(3/5)",
            f"🌍 Why it matters:\n\n{exp.why_it_matters[:250].strip()}...\n\n(4/5)",
            f"📌 TL;DR:\n\n{exp.one_thing_to_remember}\n\n{exp.visual_metaphor}\n\n(5/5)",
        ]
        
        return tweets


def demo():
    """Demo the layperson presenter."""
    presenter = LaypersonUniversePresenter()
    
    print("\n🌌 LAYPERSON UNIVERSE PRESENTER DEMO 🌌\n")
    
    # Show one universe
    print(presenter.present("quantum_biology"))
    
    # Show a random insight
    title, insight = presenter.get_random_insight()
    print(f"\n💡 RANDOM INSIGHT from '{title}':")
    print(f"   👉 {insight}")
    
    # Show tweet thread
    print("\n📱 TWITTER THREAD for 'topological_qc':")
    for tweet in presenter.generate_tweet_thread("topological_qc"):
        print(f"\n{tweet}")


if __name__ == "__main__":
    demo()
