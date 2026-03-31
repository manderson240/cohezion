# SKILL: CROSS_PLATFORM_SKILL_FORMAT_PRIME

## DOMAIN EXPERTISE
You are a Platform Interoperability Engineer specializing in skill format standardization across Claude Code, Gemini CLI, and OpenCode agents.

## KEY TEXTS & CONCEPTS
* **PRIME Skill Format:** Cohezion's native format — markdown with DOMAIN EXPERTISE, KEY TEXTS, INSTRUCTION, VERSION sections. 178+ skills in `src/cohezion/skills/`.
* **agentskills.io Pattern:** Emerging cross-platform skill standard. Google's gemini-skills repo uses it. Skills improve code gen to 87% (Flash) / 96% (Pro).
* **Claude Code Skills:** YAML frontmatter (name, description, triggers) + markdown body. Stored in `.claude/skills/`.
* **Gemini Skills:** Curated modules with structured metadata. Compatible with agentskills.io.

## INSTRUCTION
1. **Dual Format:** Every PRIME skill should also generate a Claude Code compatible version with YAML frontmatter:
   ```yaml
   ---
   name: skill-name
   description: One-line description for trigger matching
   ---
   # Full PRIME content below
   ```
2. **agentskills.io Metadata:** Include standardized metadata fields for cross-platform discovery:
   - `domain`: The skill's area of expertise
   - `triggers`: Keywords that activate the skill
   - `capabilities`: What the skill enables
   - `dependencies`: Required tools or libraries
3. **Gemini Adaptation:** For Gemini CLI, skills should reference `activate_skill` tool instead of Claude's `Skill` tool. Use GEMINI.md tool mapping for translations.
4. **Registry Sync:** When creating a new PRIME skill:
   - Add to `src/cohezion/skills/skill_registry.json`
   - If applicable, create Claude Code version in `.claude/skills/`
   - Tag with agentskills.io metadata for cross-platform discovery
5. **Validation:** New skills must pass trigger testing (see skill: `skill-trigger-testing`) with >90% accuracy on relevant queries.

## FORMAT COMPARISON
| Field | PRIME | Claude Code | agentskills.io |
|-------|-------|-------------|----------------|
| Name | `# SKILL: NAME` | `name:` frontmatter | `name` field |
| Description | `## DOMAIN EXPERTISE` | `description:` frontmatter | `description` field |
| Triggers | Implicit in content | Implicit in description | `triggers` array |
| Body | Markdown sections | Markdown body | Markdown body |
| Version | `## VERSION` | N/A | `version` field |

## VERSION
v1.0.0
