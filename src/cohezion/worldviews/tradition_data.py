"""Indigenous cosmological traditions mapped to the 10-step Theory of Everything chain.

Each tradition encodes its own path through the same universal structure:
Nothing -> Quadrature -> 12 Parameters -> 4 Fabrics -> Phase ->
Symmetry Breaking -> SPIN -> HIHO -> COHESION -> Reality Precipitates
"""

from __future__ import annotations

from dataclasses import dataclass


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
    """Maps one ToE step to its indigenous equivalent."""

    step_index: int
    step_name: str
    indigenous_term: str
    description: str
    physics_parallel: str

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "step_name": self.step_name,
            "indigenous_term": self.indigenous_term,
            "description": self.description,
            "physics_parallel": self.physics_parallel,
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
    """A single indigenous cosmological tradition with its 10-step ToE mapping."""

    name: str
    slug: str
    origin_region: str
    step_mappings: tuple[StepMapping, ...]
    unique_contributions: tuple[UniqueContribution, ...]

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
            "ground_state_name": self.ground_state_name,
            "hiho_name": self.hiho_name,
            "cohesion_name": self.cohesion_name,
            "witness_mark_type": self.witness_mark_type,
        }


@dataclass(frozen=True)
class Convergence:
    """A cross-tradition convergence pattern."""

    category: str
    description: str
    traditions_involved: tuple[str, ...]
    toe_steps: tuple[int, ...]

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "traditions_involved": list(self.traditions_involved),
            "toe_steps": list(self.toe_steps),
        }


# ─── Helper to build step tuples concisely ──────────────────────────────


def _steps(*entries: tuple[str, str, str]) -> tuple[StepMapping, ...]:
    """Build a tuple of 10 StepMappings from (term, desc, physics) triples."""
    assert len(entries) == 10, f"Expected 10 steps, got {len(entries)}"
    return tuple(
        StepMapping(
            step_index=i,
            step_name=TOE_STEPS[i],
            indigenous_term=term,
            description=desc,
            physics_parallel=phys,
        )
        for i, (term, desc, phys) in enumerate(entries)
    )


# ─── 16 Traditions ──────────────────────────────────────────────────────

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
            "Four-section kinship (moieties)",
            "Dual moiety system organizing all relationships",
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


# ─── Registry ───────────────────────────────────────────────────────────

_ALL_TRADITIONS: tuple[Tradition, ...] = (
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
)

_BY_SLUG: dict[str, Tradition] = {t.slug: t for t in _ALL_TRADITIONS}


def get_traditions() -> list[Tradition]:
    return list(_ALL_TRADITIONS)


def get_tradition(slug: str) -> Tradition | None:
    return _BY_SLUG.get(slug)


def get_step_across_traditions(step_index: int) -> list[dict]:
    """Return all 16 traditions' mapping for a given step (0-9)."""
    if not 0 <= step_index <= 9:
        raise ValueError(f"Step index must be 0-9, got {step_index}")
    return [
        {
            "tradition": t.name,
            "slug": t.slug,
            "indigenous_term": t.step_mappings[step_index].indigenous_term,
            "description": t.step_mappings[step_index].description,
            "physics_parallel": t.step_mappings[step_index].physics_parallel,
        }
        for t in _ALL_TRADITIONS
    ]


# ─── Convergences ───────────────────────────────────────────────────────

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
