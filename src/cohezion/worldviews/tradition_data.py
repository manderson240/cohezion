"""Cultural and religious cosmologies, with Cohezion's interpretive 10-step ToE mapping.

STATUS — read before using any of this data:

* The 10-step chain (Nothing -> Quadrature -> 12 Parameters -> 4 Fabrics -> Phase ->
  Symmetry Breaking -> SPIN -> HIHO -> COHESION -> Reality Precipitates) is COHEZION'S
  OWN framework. It is not a structure these traditions share or assert. Placing a
  tradition's concept in one of its slots is Cohezion's interpretive analogy.
* The mappings were generated in bulk (95be0e4bf, 2026-03-27) and have NOT been reviewed
  by the communities concerned. No community consent or authority is recorded for them.
  Each ``StepMapping.provenance`` says so ("generated, unreviewed") until a source exists.
* ``cohezion_analogy`` (formerly ``physics_parallel``) is Cohezion's analogy, not a
  claim made by the tradition. Many entries merely restate the step name.
* Convergences are produced by the mapping template (every entry must fill every slot),
  so they are interpretive, not empirical findings.
* Speculative/fringe-physics frameworks (``stealthskater``) are NOT traditions and are
  kept in a separate registry (``get_speculative_frameworks``) so they never share
  standing with Indigenous and religious traditions.

Context: Richards et al. 2026, "Ancient apocalypse now", Australian Archaeology 92(2),
doi:10.1080/03122417.2026.2706246 — pseudoarchaeology markers (conclusion-first
selection, stripped context, fringe given equal standing).
"""

from __future__ import annotations

from dataclasses import dataclass


INTERPRETIVE_NOTICE: str = (
    "Interpretive, unreviewed: the 10-step ToE mapping is Cohezion's own analogy, "
    "generated without review by, or consent from, the communities concerned. It is not "
    "a statement of any tradition's beliefs or Law. Traditions should be understood in "
    "their own terms, from their own knowledge holders."
)

DEFAULT_PROVENANCE: str = "generated, unreviewed"

CATEGORY_TRADITION: str = "cultural-tradition"
CATEGORY_SPECULATIVE: str = "speculative-physics"

CONVERGENCE_BASIS: str = (
    "interpretive: produced by Cohezion's 10-slot mapping template, not an empirical finding"
)


# The 10-step Theory of Everything chain
TOE_STEPS: list[str] = [
    "Nothing (Ground State)",
    "Quadrature (First Distinction)",
    "12 Parameters (Degrees of Freedom)",
    "4 Fabrics (Domains)",
    "Phase (Oscillation)",
    "Symmetry Breaking (Differentiation)",
    "SPIN (Information Unit)",
    "HIHO (Dynamic Equilibrium)",
    "COHESION (Binding Principle)",
    "Reality Precipitates (Witness Marks)",
]


@dataclass(frozen=True)
class StepMapping:
    """Cohezion's interpretive placement of one tradition concept in one ToE step.

    ``cohezion_analogy`` is Cohezion's analogy, not the tradition's claim.
    ``provenance`` records the source of the mapping; "generated, unreviewed" means none.
    """

    step_index: int
    step_name: str
    indigenous_term: str
    description: str
    cohezion_analogy: str
    provenance: str = DEFAULT_PROVENANCE

    @property
    def physics_parallel(self) -> str:
        """Deprecated alias of ``cohezion_analogy`` (it was never a physics finding)."""
        return self.cohezion_analogy

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "step_name": self.step_name,
            "indigenous_term": self.indigenous_term,
            "description": self.description,
            "cohezion_analogy": self.cohezion_analogy,
            "physics_parallel": self.cohezion_analogy,  # deprecated key, kept for readers
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class UniqueContribution:
    """What only this tradition contributes to the synthesis."""

    aspect: str
    description: str

    def to_dict(self) -> dict:
        return {"aspect": self.aspect, "description": self.description}


@dataclass(frozen=True)
class Tradition:
    """A registry entry with Cohezion's interpretive 10-step ToE mapping.

    ``category`` separates cultural/religious traditions from speculative frameworks.
    ``scope_note`` flags entries that generalise across many distinct peoples.
    """

    name: str
    slug: str
    origin_region: str
    step_mappings: tuple[StepMapping, ...]
    unique_contributions: tuple[UniqueContribution, ...]
    category: str = CATEGORY_TRADITION
    scope_note: str = ""

    @property
    def ground_state_name(self) -> str:
        return self.step_mappings[0].indigenous_term

    @property
    def hiho_name(self) -> str:
        return self.step_mappings[7].indigenous_term

    @property
    def cohesion_name(self) -> str:
        return self.step_mappings[8].indigenous_term

    @property
    def witness_mark_type(self) -> str:
        return self.step_mappings[9].indigenous_term

    def get_step(self, index: int) -> StepMapping:
        if not 0 <= index <= 9:
            raise ValueError(f"Step index must be 0-9, got {index}")
        return self.step_mappings[index]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "slug": self.slug,
            "origin_region": self.origin_region,
            "category": self.category,
            "scope_note": self.scope_note,
            "ground_state_name": self.ground_state_name,
            "hiho_name": self.hiho_name,
            "cohesion_name": self.cohesion_name,
            "witness_mark_type": self.witness_mark_type,
            "step_mappings": [s.to_dict() for s in self.step_mappings],
            "unique_contributions": [u.to_dict() for u in self.unique_contributions],
        }

    def to_summary(self) -> dict:
        return {
            "name": self.name,
            "slug": self.slug,
            "origin_region": self.origin_region,
            "category": self.category,
            "scope_note": self.scope_note,
            "ground_state_name": self.ground_state_name,
            "hiho_name": self.hiho_name,
            "cohesion_name": self.cohesion_name,
            "witness_mark_type": self.witness_mark_type,
        }


@dataclass(frozen=True)
class Convergence:
    """A cross-tradition pattern produced by the mapping template (interpretive)."""

    category: str
    description: str
    traditions_involved: tuple[str, ...]
    toe_steps: tuple[int, ...]
    basis: str = CONVERGENCE_BASIS

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "basis": self.basis,
            "description": self.description,
            "traditions_involved": list(self.traditions_involved),
            "toe_steps": list(self.toe_steps),
        }


# ─── Helper to build step tuples concisely ──────────────────────────────


def _steps(*entries: tuple[str, ...]) -> tuple[StepMapping, ...]:
    """Build 10 StepMappings from (term, desc, analogy[, provenance]) tuples.

    Provenance defaults to "generated, unreviewed"; supply a 4th element only when a
    real, checkable source exists.
    """
    if len(entries) != 10:
        raise ValueError(f"Expected 10 steps, got {len(entries)}")
    return tuple(
        StepMapping(
            step_index=i,
            step_name=TOE_STEPS[i],
            indigenous_term=entry[0],
            description=entry[1],
            cohezion_analogy=entry[2],
            provenance=entry[3] if len(entry) > 3 else DEFAULT_PROVENANCE,
        )
        for i, entry in enumerate(entries)
    )


# ─── 17 cultural/religious traditions (interpretive mappings) ──────────────────────────────────────────────────────

_LAKOTA = Tradition(
    name="Lakota",
    slug="lakota",
    origin_region="Great Plains, North America",
    step_mappings=_steps(
        (
            "Wakan Tanka",
            "The Great Mystery, sacred incomprehensibility",
            "Vacuum state / quantum void",
        ),
        (
            "First song/prayer",
            "The first sacred utterance that splits silence",
            "Symmetry breaking from void",
        ),
        (
            "12 moons / sacred directions",
            "Seasonal and directional framework",
            "12 degrees of freedom",
        ),
        ("Four winds / cardinal directions", "Spiritual governance of space", "4 fabric domains"),
        (
            "Drum heartbeat / seasonal cycles",
            "Rhythmic pulsation of sacred time",
            "Phase oscillation",
        ),
        (
            "Inipi (sweat lodge) / vision quest threshold",
            "Purification that differentiates seeker from world",
            "Symmetry breaking",
        ),
        (
            "Sacred hoop / medicine wheel",
            "Information encoded in circular completeness",
            "SPIN information unit",
        ),
        (
            "Vision Quest",
            "Sustained oscillation between worlds seeking balance",
            "HIHO dynamic equilibrium",
        ),
        (
            "Mitakuye Oyasin",
            "We Are All Related — total interconnection",
            "COHESION binding principle",
        ),
        ("Petroglyphs", "Stone carvings as permanent witness marks", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Relational ontology", "Mitakuye Oyasin as binding principle — reality IS relationship"
        ),
        UniqueContribution(
            "Vision quest protocol", "Structured threshold crossing as HIHO calibration"
        ),
    ),
)

_VEDIC = Tradition(
    name="Vedic",
    slug="vedic",
    origin_region="Indian Subcontinent",
    step_mappings=_steps(
        (
            "Brahman",
            "The absolute ground of all being, without qualities",
            "Vacuum state / quantum void",
        ),
        (
            "Om / Nada Brahma",
            "Primordial vibration that initiates creation",
            "Symmetry breaking from void",
        ),
        (
            "12 Adityas / zodiac houses",
            "Solar deities governing cosmic order",
            "12 degrees of freedom",
        ),
        ("Purushartha (4 aims of life)", "Dharma, Artha, Kama, Moksha", "4 fabric domains"),
        ("Yugas / cyclic time", "Cosmic ages cycling through creation", "Phase oscillation"),
        (
            "Maya / Prakriti differentiation",
            "Illusion that separates the manifest from unmanifest",
            "Symmetry breaking",
        ),
        (
            "Chakra / Kundalini",
            "Energy vortices encoding life-force information",
            "SPIN information unit",
        ),
        ("Yoga", "Union of opposites — disciplined balance practice", "HIHO dynamic equilibrium"),
        (
            "Dharma / Karma",
            "Cosmic law binding action to consequence",
            "COHESION binding principle",
        ),
        ("Mantra / Scripture", "Sacred texts as crystallized knowledge", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Mathematical precision", "Explicit zero, infinity, and cyclic cosmology"
        ),
        UniqueContribution("Consciousness ontology", "Brahman as both ground state AND observer"),
    ),
)

_DAOIST = Tradition(
    name="Daoist",
    slug="daoist",
    origin_region="China",
    step_mappings=_steps(
        ("Wu / Wuji", "Undifferentiated emptiness, the limitless", "Vacuum state / quantum void"),
        (
            "Taiji (Supreme Ultimate)",
            "First polarity emergence — yin/yang",
            "Symmetry breaking from void",
        ),
        ("12 Earthly Branches", "Zodiac cycle governing time and space", "12 degrees of freedom"),
        ("Si Xiang (Four Symbols)", "Greater/Lesser Yin and Yang", "4 fabric domains"),
        (
            "Qi circulation / seasonal flow",
            "Vital breath cycling through meridians",
            "Phase oscillation",
        ),
        (
            "Yin-Yang differentiation",
            "Complementary opposites separating from unity",
            "Symmetry breaking",
        ),
        (
            "Bagua (8 trigrams)",
            "Binary information encoding in trigram combinations",
            "SPIN information unit",
        ),
        ("Wu Wei", "Effortless action — acting without forcing", "HIHO dynamic equilibrium"),
        (
            "Dao",
            "The Way — the unnamed binding principle of all things",
            "COHESION binding principle",
        ),
        (
            "I Ching / Calligraphy",
            "Divination text and brush arts as witness marks",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution("Binary encoding", "Bagua trigrams as proto-digital information"),
        UniqueContribution("Wu Wei principle", "Non-action as optimal dynamic equilibrium"),
    ),
)

_YORUBA = Tradition(
    name="Yoruba",
    slug="yoruba",
    origin_region="West Africa (Nigeria, Benin)",
    step_mappings=_steps(
        ("Olodumare", "Supreme creative force, source of all ase", "Vacuum state / quantum void"),
        (
            "Olodumare's breath / first word",
            "Divine utterance initiating creation",
            "Symmetry breaking from void",
        ),
        (
            "16 Odu Ifa principal figures",
            "Primary divination patterns (16 > 12 but maps)",
            "12 degrees of freedom",
        ),
        (
            "Four cardinal Orisha",
            "Obatala, Ogun, Sango, Yemoja governing domains",
            "4 fabric domains",
        ),
        ("Festival / ritual calendar", "Annual ceremonial cycles of renewal", "Phase oscillation"),
        (
            "Orisha differentiation from Olodumare",
            "Divine aspects separating into distinct powers",
            "Symmetry breaking",
        ),
        (
            "Ase (vital force)",
            "Power-to-make-things-happen encoded in speech/action",
            "SPIN information unit",
        ),
        (
            "Ifa divination",
            "Babalawo casting to find balance between forces",
            "HIHO dynamic equilibrium",
        ),
        (
            "Ase (binding force)",
            "The connective power sustaining all relationships",
            "COHESION binding principle",
        ),
        (
            "Ifa corpus",
            "256 Odu verses — oral knowledge crystallized in poetry",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution("256 Odu system", "Complete combinatorial knowledge system"),
        UniqueContribution(
            "Ase as dual principle", "Same force serves both SPIN and COHESION roles"
        ),
    ),
)

_HAUDENOSAUNEE = Tradition(
    name="Haudenosaunee",
    slug="haudenosaunee",
    origin_region="Northeast North America (Iroquois Confederacy)",
    step_mappings=_steps(
        (
            "Sky World",
            "The primordial realm above, source of all creation",
            "Vacuum state / quantum void",
        ),
        (
            "Sky Woman's fall",
            "The first being descends, initiating the world",
            "Symmetry breaking from void",
        ),
        (
            "Clan system / seasonal ceremonies",
            "Governance through relational structures",
            "12 degrees of freedom",
        ),
        ("Four sacred ceremonies", "Midwinter, Maple, Strawberry, Green Corn", "4 fabric domains"),
        (
            "Seasonal ceremonial cycle",
            "Annual rhythm of thanksgiving and renewal",
            "Phase oscillation",
        ),
        (
            "Twinship (Sapling vs Flint)",
            "Creative and destructive principles separating",
            "Symmetry breaking",
        ),
        (
            "Wampum encoding",
            "Shell bead patterns recording treaties and law",
            "SPIN information unit",
        ),
        (
            "Consensus (Kaianerekowa)",
            "Great Law requiring unanimous agreement",
            "HIHO dynamic equilibrium",
        ),
        (
            "Sken:nen (Peace)",
            "The Great Peace binding all nations together",
            "COHESION binding principle",
        ),
        ("Wampum belts", "Treaty records in beadwork as permanent witness", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Consensus governance", "HIHO as political process — decisions require equilibrium"
        ),
        UniqueContribution(
            "Seven-generation thinking", "Time-extended COHESION spanning past and future"
        ),
    ),
)

_HOPI = Tradition(
    name="Hopi",
    slug="hopi",
    origin_region="Southwest North America (Arizona)",
    step_mappings=_steps(
        ("Taiowa", "The Creator who existed in infinite space", "Vacuum state / quantum void"),
        (
            "Sotuknang / first creation",
            "Taiowa's nephew creates the first world",
            "Symmetry breaking from void",
        ),
        (
            "Clan migrations / directional teachings",
            "Migration patterns through multiple worlds",
            "12 degrees of freedom",
        ),
        ("Four Worlds", "Sequential worlds of creation, each with lessons", "4 fabric domains"),
        (
            "Kachina seasonal cycle",
            "Spirit beings arriving and departing cyclically",
            "Phase oscillation",
        ),
        (
            "World destruction / recreation",
            "Each world ending to begin anew with refinement",
            "Symmetry breaking",
        ),
        (
            "Corn / prayer feathers",
            "Sacred objects encoding spiritual information",
            "SPIN information unit",
        ),
        (
            "Kachina ceremony",
            "Ceremonial dance restoring cosmic balance",
            "HIHO dynamic equilibrium",
        ),
        (
            "Remembering the Creator",
            "Maintaining relationship with Taiowa as binding duty",
            "COHESION binding principle",
        ),
        ("Petroglyphs", "Rock art recording prophecy and migration routes", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Four Worlds cosmology", "Sequential reality iterations as fabric domains"
        ),
        UniqueContribution("Prophecy stone", "Witness marks encoding future states"),
    ),
)

_DINE = Tradition(
    name="Dine (Navajo)",
    slug="dine",
    origin_region="Southwest North America",
    step_mappings=_steps(
        (
            "First Man / First Woman",
            "Primordial beings in the dark lower world",
            "Vacuum state / quantum void",
        ),
        (
            "Emergence through four worlds",
            "Ascending through layered realities",
            "Symmetry breaking from void",
        ),
        (
            "Holy People / sacred mountains",
            "Spiritual beings and landscape anchors",
            "12 degrees of freedom",
        ),
        (
            "Four sacred mountains",
            "Blanca Peak, Mt Taylor, San Francisco Peaks, Hesperus",
            "4 fabric domains",
        ),
        (
            "Ceremony calendar / seasonal rites",
            "Healing ceremonies tied to natural cycles",
            "Phase oscillation",
        ),
        (
            "Monster Slayer / Born for Water",
            "Hero twins separating order from chaos",
            "Symmetry breaking",
        ),
        (
            "Corn pollen / sacred songs",
            "Ritual elements encoding spiritual data",
            "SPIN information unit",
        ),
        (
            "Healing ceremony (Blessingway)",
            "Multi-day rites restoring harmony",
            "HIHO dynamic equilibrium",
        ),
        (
            "Hozho",
            "Walking in beauty — total harmony with all existence",
            "COHESION binding principle",
        ),
        ("Sand paintings", "Ephemeral art destroyed after healing", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Ephemeral witness marks",
            "Sand paintings intentionally destroyed — impermanence as principle",
        ),
        UniqueContribution("Hozho aesthetics", "Beauty as the name for COHESION"),
    ),
)

_MAORI = Tradition(
    name="Maori",
    slug="maori",
    origin_region="Aotearoa (New Zealand)",
    step_mappings=_steps(
        ("Te Kore", "The Void — realm of potential being", "Vacuum state / quantum void"),
        ("Te Po (The Night)", "Darkness from which light emerges", "Symmetry breaking from void"),
        (
            "Genealogical layers (whakapapa)",
            "Descent lines encoding cosmic structure",
            "12 degrees of freedom",
        ),
        (
            "Four winds / Atua domains",
            "Tangaroa (sea), Tane (forest), Tu (war), Rongo (peace)",
            "4 fabric domains",
        ),
        ("Maramataka (lunar calendar)", "Moon-phase governance of activity", "Phase oscillation"),
        (
            "Separation of Rangi and Papa",
            "Sky Father and Earth Mother pulled apart",
            "Symmetry breaking",
        ),
        (
            "Haka / waiata",
            "Performative knowledge encoding in body and voice",
            "SPIN information unit",
        ),
        (
            "Powhiri",
            "Welcome ceremony — encounter protocol for balance",
            "HIHO dynamic equilibrium",
        ),
        ("Aroha", "Love as the binding force of all relationships", "COHESION binding principle"),
        ("Ta moko", "Facial tattoo encoding identity and lineage", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Whakapapa ontology", "Reality IS genealogy — everything connected by descent"
        ),
        UniqueContribution(
            "Body as witness mark", "Ta moko inscribes knowledge onto the living person"
        ),
    ),
)

_INUIT = Tradition(
    name="Inuit",
    slug="inuit",
    origin_region="Arctic (Circumpolar North)",
    scope_note=(
        "Inuit communities across Alaska, Inuit Nunangat (Canada) and Kalaallit Nunaat "
        "(Greenland) have distinct dialects, stories and practices. This entry generalises "
        "across them; terms and their meanings vary by region."
    ),
    step_mappings=_steps(
        (
            "Sila",
            "The breath/weather/consciousness permeating everything",
            "Vacuum state / quantum void",
        ),
        (
            "Raven / first light",
            "Trickster bringing light from primordial darkness",
            "Symmetry breaking from void",
        ),
        (
            "Animal spirits / seasonal markers",
            "Spirit beings governing ecological time",
            "12 degrees of freedom",
        ),
        (
            "Four seasons / cardinal winds",
            "Arctic seasonal extremes as domain boundaries",
            "4 fabric domains",
        ),
        (
            "Ice/thaw cycle / animal migrations",
            "Environmental oscillation governing all life",
            "Phase oscillation",
        ),
        ("Shamanic soul flight", "Angakkuq separating spirit from body", "Symmetry breaking"),
        (
            "Drum songs / throat singing",
            "Vibrational knowledge encoding in sound",
            "SPIN information unit",
        ),
        (
            "Drum trance",
            "Rhythmic altered state achieving cosmic balance",
            "HIHO dynamic equilibrium",
        ),
        ("Isuma", "Thinking-feeling wisdom binding community", "COHESION binding principle"),
        ("Carved amulets", "Ivory and bone carvings as spiritual records", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Sila as ambient consciousness",
            "Ground state is simultaneously weather, breath, and mind",
        ),
        UniqueContribution(
            "Extreme environment cosmology", "Ice/thaw as primary phase oscillation"
        ),
    ),
)

_NORSE = Tradition(
    name="Norse",
    slug="norse",
    origin_region="Scandinavia / Northern Europe",
    step_mappings=_steps(
        ("Ginnungagap", "The yawning void between fire and ice", "Vacuum state / quantum void"),
        (
            "Fire/Ice collision (Muspelheim/Niflheim)",
            "Opposites meeting to create first being",
            "Symmetry breaking from void",
        ),
        (
            "Nine Worlds / runic alphabet",
            "Interconnected realms on Yggdrasil",
            "12 degrees of freedom",
        ),
        (
            "Four dwarfs (cardinal pillars)",
            "Nordri, Sudri, Austri, Vestri holding up the sky",
            "4 fabric domains",
        ),
        ("Ragnarok cycle", "Cosmic destruction and renewal cycle", "Phase oscillation"),
        (
            "Odin's sacrifice on Yggdrasil",
            "Self-sacrifice to gain wisdom — separation through ordeal",
            "Symmetry breaking",
        ),
        ("Runes", "Sacred alphabet encoding cosmic knowledge", "SPIN information unit"),
        ("Seidr trance", "Shamanic practice for perceiving fate", "HIHO dynamic equilibrium"),
        (
            "Wyrd / Orlog",
            "Fate-web connecting all actions across time",
            "COHESION binding principle",
        ),
        ("Rune carvings", "Stone inscriptions as permanent records", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Ginnungagap polarity", "Void defined by fire/ice tension — ground state has structure"
        ),
        UniqueContribution(
            "Wyrd as causal web", "Fate is not linear but a woven network of consequence"
        ),
    ),
)

_CELTIC = Tradition(
    name="Celtic",
    slug="celtic",
    origin_region="Western Europe (Ireland, Britain, Gaul)",
    step_mappings=_steps(
        (
            "Three Worlds (Land, Sea, Sky)",
            "Tripartite cosmos as ground structure",
            "Vacuum state / quantum void",
        ),
        (
            "Otherworld irruption",
            "The Sidhe realm breaking through into this world",
            "Symmetry breaking from void",
        ),
        (
            "Ogham alphabet / tree calendar",
            "20 tree-letters mapping cosmic knowledge",
            "12 degrees of freedom",
        ),
        (
            "Four treasures / provinces",
            "Sword, Spear, Cauldron, Stone of the four kingdoms",
            "4 fabric domains",
        ),
        (
            "Samhain/Beltane cycle",
            "Fire festivals marking the thinning of veils",
            "Phase oscillation",
        ),
        (
            "Hero's transformation",
            "Cu Chulainn's warp-spasm — identity breaking and reforming",
            "Symmetry breaking",
        ),
        (
            "Ogham inscriptions",
            "Tree-alphabet encoding on standing stones",
            "SPIN information unit",
        ),
        (
            "Thin place crossing",
            "Liminal spaces where worlds interpenetrate",
            "HIHO dynamic equilibrium",
        ),
        (
            "Geis + Dana",
            "Sacred obligation + divine generosity binding society",
            "COHESION binding principle",
        ),
        ("Ogham stones", "Standing stones with carved tree-alphabet", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Thin places", "HIHO as spatial phenomenon — locations where equilibrium is accessible"
        ),
        UniqueContribution("Tripartite ground", "Ground state already has threefold structure"),
    ),
)

_SHINTO = Tradition(
    name="Shinto",
    slug="shinto",
    origin_region="Japan",
    step_mappings=_steps(
        (
            "Ame-tsuchi (Heaven and Earth)",
            "Primordial separation of high and low plains",
            "Vacuum state / quantum void",
        ),
        (
            "Kuni-umi (land-birthing)",
            "Izanagi and Izanami stirring the cosmic brine",
            "Symmetry breaking from void",
        ),
        (
            "Kami (myriad spirits)",
            "800 myriads of divine spirits in all things",
            "12 degrees of freedom",
        ),
        (
            "Four seasons / directional kami",
            "Seasonal governance and directional spirits",
            "4 fabric domains",
        ),
        (
            "Matsuri (festival cycle)",
            "Annual shrine festivals cycling through sacred time",
            "Phase oscillation",
        ),
        (
            "Amaterasu emerging from cave",
            "Light returning after withdrawal — dramatic differentiation",
            "Symmetry breaking",
        ),
        (
            "Kotodama (word-spirit power)",
            "Sacred words carrying creative force",
            "SPIN information unit",
        ),
        ("Kagura dance", "Sacred dance restoring divine harmony", "HIHO dynamic equilibrium"),
        (
            "Musubi",
            "Creative interconnection — the binding power of kami",
            "COHESION binding principle",
        ),
        (
            "Kotodama (inscribed)",
            "Word-spirit preserved in ritual and text",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution(
            "Radical immanence", "Every object contains kami — no nature/spirit divide"
        ),
        UniqueContribution(
            "Musubi as creative binding", "COHESION is generative, not just connective"
        ),
    ),
)

_ANDEAN = Tradition(
    name="Andean",
    slug="andean",
    origin_region="Andes (Peru, Bolivia, Ecuador)",
    scope_note=(
        "This entry mixes concepts from distinct Andean peoples (including Quechua- and "
        "Aymara-speaking communities) and from the Inca state (e.g. Tawantinsuyu, ceque "
        "lines), across different periods. It generalises and should not be read as the "
        "worldview of any one community."
    ),
    step_mappings=_steps(
        ("Pachamama", "Earth Mother as living ground of all being", "Vacuum state / quantum void"),
        (
            "Viracocha's emergence",
            "Creator rising from Lake Titicaca",
            "Symmetry breaking from void",
        ),
        (
            "Ceque lines / sacred sites",
            "Radiating lines connecting huacas (sacred places)",
            "12 degrees of freedom",
        ),
        (
            "Four suyus (quarters)",
            "Tawantinsuyu — the four-part empire of the world",
            "4 fabric domains",
        ),
        (
            "Solstice / Inti Raymi cycle",
            "Solar festivals governing agricultural time",
            "Phase oscillation",
        ),
        ("Pachakuti (world reversal)", "Cosmic inversion that resets the age", "Symmetry breaking"),
        (
            "Quipu knots",
            "Knotted string encoding numerical and narrative data",
            "SPIN information unit",
        ),
        (
            "Despacho ceremony",
            "Offering ritual restoring reciprocal balance",
            "HIHO dynamic equilibrium",
        ),
        (
            "Ayni",
            "Sacred reciprocity — mutual exchange binding all relations",
            "COHESION binding principle",
        ),
        (
            "Quipu / Weavings",
            "Textile and knot records as knowledge storage",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution("Ayni reciprocity", "COHESION as economic and spiritual exchange"),
        UniqueContribution("Quipu encoding", "Three-dimensional data storage in knotted strings"),
    ),
)

_AMAZONIAN = Tradition(
    name="Amazonian",
    slug="amazonian",
    origin_region="Amazon Basin (South America)",
    scope_note=(
        "The Amazon basin is home to hundreds of distinct Indigenous peoples and languages "
        "with different cosmologies and practices. This entry generalises across them and "
        "draws partly on anthropological frameworks (e.g. perspectivism) rather than on "
        "any one people's own account."
    ),
    step_mappings=_steps(
        (
            "Forest Intelligence",
            "The living forest as distributed sentient ground",
            "Vacuum state / quantum void",
        ),
        (
            "Anaconda / jaguar emergence",
            "Primal beings differentiating from forest-mind",
            "Symmetry breaking from void",
        ),
        (
            "Plant teacher spirits",
            "Specific plant intelligences governing knowledge domains",
            "12 degrees of freedom",
        ),
        ("Four directions / river systems", "Watershed and cardinal framework", "4 fabric domains"),
        (
            "Flood/dry cycle / fruiting seasons",
            "Hydrological oscillation governing life",
            "Phase oscillation",
        ),
        (
            "Shapeshifting / perspectivism",
            "Beings switching forms — identity is perspective-dependent",
            "Symmetry breaking",
        ),
        (
            "Geometric visions (phosphenes)",
            "Entoptic patterns encoding universal structures",
            "SPIN information unit",
        ),
        (
            "Visionary crossing (ayahuasca)",
            "Plant-mediated boundary crossing for cosmic balance",
            "HIHO dynamic equilibrium",
        ),
        (
            "Relational web",
            "All beings connected through reciprocal predation/kinship",
            "COHESION binding principle",
        ),
        ("Icaros", "Healing songs learned from plant spirits", "Reality precipitates"),
    ),
    unique_contributions=(
        UniqueContribution(
            "Perspectivism",
            "All beings share culture; bodies are the variable — radical ontological relativity",
        ),
        UniqueContribution(
            "Plant-mediated HIHO", "Biochemical technology for equilibrium crossing"
        ),
    ),
)

_DOGON = Tradition(
    name="Dogon",
    slug="dogon",
    origin_region="Mali, West Africa",
    step_mappings=_steps(
        (
            "Amma's egg",
            "The primordial cosmic egg containing all potential",
            "Vacuum state / quantum void",
        ),
        (
            "Amma's vibration / word",
            "First vibratory word cracking the egg",
            "Symmetry breaking from void",
        ),
        (
            "266 signs of creation",
            "Complete symbolic system of cosmic order",
            "12 degrees of freedom",
        ),
        (
            "Four clavicle pairs",
            "Paired structural elements of the cosmic body",
            "4 fabric domains",
        ),
        ("Sigui cycle (60 years)", "Major ceremonial cycle tracking Sirius", "Phase oscillation"),
        (
            "Nommo sacrifice",
            "The first being sacrificed to create differentiation",
            "Symmetry breaking",
        ),
        ("Granary symbolism", "Architecture encoding cosmic structure", "SPIN information unit"),
        ("Forge work", "Blacksmith as cosmic mediator between forces", "HIHO dynamic equilibrium"),
        (
            "Nommo life-force",
            "Ancestral water-spirit binding all existence",
            "COHESION binding principle",
        ),
        (
            "266 signs (inscribed)",
            "Complete sign system carved and transmitted",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution(
            "Cosmic egg ontology", "Ground state has internal structure — egg, not void"
        ),
        UniqueContribution(
            "266 sign system", "Exhaustive symbolic encoding rivaling mathematical completeness"
        ),
    ),
)

_ABORIGINAL = Tradition(
    name="Aboriginal Australian",
    slug="aboriginal",
    origin_region="Australia",
    scope_note=(
        "Aboriginal Australia comprises hundreds of distinct nations and languages, each "
        "with its own Law, stories and practices. This entry generalises across them and "
        "must not be read as the Law of any one nation. Terms such as Tjukurpa belong to "
        "particular language groups (Tjukurpa is Western Desert usage)."
    ),
    step_mappings=_steps(
        (
            "Dreaming / Tjukurpa",
            "The eternal now — time before and during creation",
            "Vacuum state / quantum void",
        ),
        (
            "Ancestor beings waking",
            "Rainbow Serpent and others singing the world into being",
            "Symmetry breaking from void",
        ),
        (
            "Songline network / totemic sites",
            "Landscape-encoded knowledge pathways",
            "12 degrees of freedom",
        ),
        (
            "Section systems (four-section kinship)",
            "In nations that use them, section systems divide society into four named "
            "sections that shape kinship and marriage. They are distinct from two-part "
            "moiety systems and from eight-part subsection systems; nations differ in "
            "which of these they use, and some use none. (Corrected 2026-09-21: this row "
            "previously labelled four-section kinship as moieties, which are two-part.)",
            "4 fabric domains",
        ),
        (
            "Wet/dry seasonal rhythm",
            "Environmental oscillation governing ceremony and movement",
            "Phase oscillation",
        ),
        (
            "Initiation / scarification",
            "Body modification marking transition between states",
            "Symmetry breaking",
        ),
        (
            "Dot painting / body design",
            "Visual encoding of Dreaming knowledge",
            "SPIN information unit",
        ),
        (
            "Songline walking",
            "Moving through country while singing — embodied equilibrium",
            "HIHO dynamic equilibrium",
        ),
        (
            "Kinship system",
            "All-encompassing relational network binding people and land",
            "COHESION binding principle",
        ),
        (
            "Songlines",
            "Landscape-scale songs as permanent knowledge records",
            "Reality precipitates",
        ),
    ),
    unique_contributions=(
        UniqueContribution("Landscape as text", "The entire continent is a readable document"),
        UniqueContribution(
            "65,000-year continuity", "Longest continuous knowledge tradition on Earth"
        ),
    ),
)


_ININEW = Tradition(
    name="Ininew (Cree)",
    slug="ininew",
    origin_region="Subarctic / Great Plains, Turtle Island (Canada)",
    step_mappings=_steps(
        (
            "Kitci Manito",
            "The Great Spirit — sacred emptiness before all creation",
            "Vacuum state / quantum void",
        ),
        (
            "Tipiskawi Pisim (Night Sun)",
            "The Moon as first distinction: Night Sun emerging as peer of the Day Sun",
            "Symmetry breaking from void — the first duality",
        ),
        (
            "13 moons / 13 turtle scutes",
            "13 central scutes of Mikinak's shell = 13 lunar cycles per year; "
            "the degrees of temporal freedom encoded in living biology",
            "12 degrees of freedom (13-fold lunar calendar)",
        ),
        (
            "Four seasons / four cardinal medicines",
            "Seasonal governance of the land and its medicines",
            "4 fabric domains",
        ),
        (
            "28-day lunar cycle / 28 turtle edge scutes",
            "28 edge scutes = 28 days in one moon; the phase rhythm embedded in the turtle's body",
            "Phase oscillation",
        ),
        (
            "Mikinak chosen after the flood",
            "Creator Kitci Manito chooses the turtle as cosmic foundation; dry land "
            "rises from water on the turtle's back — differentiation of earth from sea",
            "Symmetry breaking — differentiation of domains",
        ),
        (
            "Turtle shell calendar",
            "The living shell encodes year (13 scutes) and month (28 scutes) "
            "simultaneously — biology as information carrier",
            "SPIN information unit — cosmic time written in morphology",
        ),
        (
            "Tipiskawi Pisim / Pisim equilibrium",
            "Night Sun and Day Sun as equal luminaries in dynamic balance; "
            "neither dominates — they alternate in HIHO rhythm",
            "HIHO dynamic equilibrium",
        ),
        (
            "Waskitow (ecological relatedness)",
            "Moon governs weather, plants, animals, temperature — all life is "
            "bound in one relational system through lunar rhythm",
            "COHESION binding principle",
        ),
        (
            "Turtle Island",
            "The continent itself as permanent witness mark — Mikinak's back "
            "as the living foundation of the world",
            "Reality precipitates — geological witness mark",
        ),
    ),
    unique_contributions=(
        UniqueContribution(
            "Biological cosmological encoding",
            "The only tradition where cosmic time (year + month) is physically "
            "embedded in a living organism's anatomy — turtle scute counts are "
            "SPIN information units realized in biology",
        ),
        UniqueContribution(
            "Dual luminary HIHO",
            "Tipiskawi Pisim (Night Sun) as equal peer of the Day Sun — "
            "a cosmological HIHO pair at the astronomical scale; "
            "equilibrium is not philosophical but structural",
        ),
    ),
)


# Restored 2026-08-01: present since #194 (b87186436) but silently dropped when this
# file was recreated in the 17-tradition rewrite — the API docstring and
# knowledge_bridge both still said "incl. stealthskater". Harness invariant S2 guards it.
# Moved 2026-09-21 OUT of the traditions registry into _SPECULATIVE_FRAMEWORKS: it is a
# fringe-physics website synthesis, not a cultural or religious tradition, and must not
# share standing with them. Content intact; get_tradition("stealthskater") still resolves.
_STEALTHSKATER = Tradition(
    name="Stealthskater Archive",
    slug="stealthskater",
    origin_region="Classified Research Archives (USA/Global)",
    category=CATEGORY_SPECULATIVE,
    scope_note=(
        "Speculative/fringe-physics synthesis drawn from a single website archive. "
        "Not a cultural or religious tradition; claims here are unverified."
    ),
    step_mappings=_steps(
        (
            "Zero-Point Field",
            "Vacuum manipulation programs -- ZPF as the ground state of all suppressed physics (Puthoff, Sarfatti)",
            "Quantum vacuum / ZPF ground",
        ),
        (
            "Quadrature Nexus",
            "Phase-conjugate EM first distinction; quadrature intersection as the first observable from vacuum (Philadelphia Experiment)",
            "First bifurcation / SU(2) quadrature axes",
        ),
        (
            "12 Scalar Parameters",
            "Sarfatti post-quantum metric = Smith 12-parameter reality; classified craft dynamics encoded in 12D manifold",
            "12D manifold / Smith FABRIC_MAP",
        ),
        (
            "4 Spacetime Fabrics",
            "Classified brane propulsion -- Area 51 craft dynamics across 4 computational/spacetime domains",
            "4 fabric domains (Space/Mass/Energy/Consciousness)",
        ),
        (
            "LENR Phase Lock",
            "Lattice confinement resonance = scalar wave coherence; cold fusion as phase-locked nuclear oscillation",
            "Phase oscillation / LENR reaction rate",
        ),
        (
            "EVO Nucleation",
            "Exotic Vacuum Object charge cluster formation = vacuum symmetry breaking (Ken Shoulders, IEEE papers)",
            "SO(12) to SO(3)^4 symmetry breaking",
        ),
        (
            "Remote Viewing SPIN",
            "Coherent SPIN-mode perceptual access across spacetime; psychotronics as structured observer-patch access",
            "SPIN information unit / observer-patch holography",
        ),
        (
            "Itonic Equilibrium",
            "Plasma HIHO threshold at 0.5 coherence; ionic cluster resonance enabling altered consciousness training",
            "HIHO dynamic equilibrium / ionic cluster state",
        ),
        (
            "Diaelectric Binding",
            "Biefield-Brown EHD field coupling as the mechanism of unified field cohesion and propulsion",
            "COHESION binding / dielectric gauge connection",
        ),
        (
            "Witness Marks",
            "Landing traces, radar returns, LENR transmutation products, declassified documents -- physical precipitates of suppressed phenomena",
            "Reality precipitates / physical evidence",
        ),
    ),
    unique_contributions=(
        UniqueContribution(
            "Institutional suppression as structural proof",
            "The pattern of classification and suppression across independent researchers validates convergence -- forbidden knowledge is forbidden precisely because it is structurally correct",
        ),
        UniqueContribution(
            "Sarfatti SU(2) consciousness bridge",
            "Direct mathematical path from SU(2) spinor algebra to conscious observation -- consciousness as a gauge degree of freedom",
        ),
        UniqueContribution(
            "Remote viewing as holographic access",
            "Puthoff-Targ protocols establish observer-patch holography from the inside -- the mind as a non-local antenna in the ZPF",
        ),
        UniqueContribution(
            "EVO-LENR nuclear-scale HIHO",
            "Exotic Vacuum Objects catalyze Low Energy Nuclear Reactions at exactly the HIHO 0.5 coherence threshold -- nuclear transmutation as witness mark of phase transition",
        ),
    ),
)


# ─── Registry ───────────────────────────────────────────────────────────

_ALL_TRADITIONS: tuple[Tradition, ...] = (  # cultural/religious traditions only
    _LAKOTA,
    _VEDIC,
    _DAOIST,
    _YORUBA,
    _HAUDENOSAUNEE,
    _HOPI,
    _DINE,
    _MAORI,
    _INUIT,
    _NORSE,
    _CELTIC,
    _SHINTO,
    _ANDEAN,
    _AMAZONIAN,
    _DOGON,
    _ABORIGINAL,
    _ININEW,
)

# Speculative / fringe-physics frameworks — a separate category, never listed as traditions.
_SPECULATIVE_FRAMEWORKS: tuple[Tradition, ...] = (_STEALTHSKATER,)

_BY_SLUG: dict[str, Tradition] = {t.slug: t for t in _ALL_TRADITIONS + _SPECULATIVE_FRAMEWORKS}


def get_traditions() -> list[Tradition]:
    """Cultural/religious traditions only (speculative frameworks excluded)."""
    return list(_ALL_TRADITIONS)


def get_speculative_frameworks() -> list[Tradition]:
    """Speculative/fringe-physics frameworks, kept apart from the traditions."""
    return list(_SPECULATIVE_FRAMEWORKS)


def get_tradition(slug: str) -> Tradition | None:
    """Resolve any registry entry by slug.

    Also resolves speculative frameworks (backward compatibility, harness S2); check
    ``.category`` before presenting the result as a tradition.
    """
    return _BY_SLUG.get(slug)


def get_step_across_traditions(step_index: int) -> list[dict]:
    """Return the 17 cultural traditions' interpretive mapping for a given step (0-9)."""
    if not 0 <= step_index <= 9:
        raise ValueError(f"Step index must be 0-9, got {step_index}")
    return [
        {
            "tradition": t.name,
            "slug": t.slug,
            "indigenous_term": t.step_mappings[step_index].indigenous_term,
            "description": t.step_mappings[step_index].description,
            "cohezion_analogy": t.step_mappings[step_index].cohezion_analogy,
            "physics_parallel": t.step_mappings[step_index].cohezion_analogy,  # deprecated
            "provenance": t.step_mappings[step_index].provenance,
        }
        for t in _ALL_TRADITIONS
    ]


# ─── Convergences ───
# Interpretive: every entry is required to fill all 10 slots, so these patterns are
# produced by the template itself. See CONVERGENCE_BASIS.────────────────────────────────────────────────────

_CONVERGENCES: tuple[Convergence, ...] = (
    Convergence(
        category="Universal Void",
        description="Every tradition begins from a state of undifferentiated potential — void, darkness, "
        "emptiness, or mystery. This maps directly to the quantum vacuum state.",
        traditions_involved=(
            "Lakota",
            "Vedic",
            "Daoist",
            "Norse",
            "Maori",
            "Aboriginal Australian",
        ),
        toe_steps=(0,),
    ),
    Convergence(
        category="Vibratory First Cause",
        description="Creation begins with sound, vibration, or utterance — Om, song, breath, word. "
        "The first distinction is oscillatory, not spatial.",
        traditions_involved=("Vedic", "Dogon", "Lakota", "Aboriginal Australian", "Shinto"),
        toe_steps=(1,),
    ),
    Convergence(
        category="Fourfold Structure",
        description="Nearly all traditions organize reality into four domains — directions, elements, "
        "seasons, or cosmic quarters — paralleling the four fabric domains.",
        traditions_involved=(
            "Lakota",
            "Vedic",
            "Daoist",
            "Haudenosaunee",
            "Hopi",
            "Dine (Navajo)",
            "Norse",
            "Celtic",
            "Andean",
            "Aboriginal Australian",
        ),
        toe_steps=(3,),
    ),
    Convergence(
        category="Cyclic Phase Dynamics",
        description="All traditions encode oscillatory time — seasons, ceremonial calendars, cosmic ages. "
        "Reality breathes rather than progresses linearly.",
        traditions_involved=(
            "Vedic",
            "Daoist",
            "Norse",
            "Hopi",
            "Andean",
            "Yoruba",
            "Dogon",
            "Aboriginal Australian",
        ),
        toe_steps=(4,),
    ),
    Convergence(
        category="Threshold/Trance Equilibrium",
        description="HIHO is accessed through structured altered states — vision quest, trance, ceremony, "
        "meditation — a universal technology for reaching dynamic equilibrium.",
        traditions_involved=(
            "Lakota",
            "Vedic",
            "Inuit",
            "Norse",
            "Celtic",
            "Amazonian",
            "Dine (Navajo)",
            "Shinto",
        ),
        toe_steps=(7,),
    ),
    Convergence(
        category="Relational Binding",
        description="COHESION is always relational — interconnection, reciprocity, kinship, harmony. "
        "No tradition treats the binding principle as mechanical or impersonal.",
        traditions_involved=(
            "Lakota",
            "Maori",
            "Haudenosaunee",
            "Andean",
            "Aboriginal Australian",
            "Amazonian",
            "Yoruba",
        ),
        toe_steps=(8,),
    ),
)


def get_convergences() -> list[Convergence]:
    return list(_CONVERGENCES)
