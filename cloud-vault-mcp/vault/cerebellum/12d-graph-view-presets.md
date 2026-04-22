---
title: "12D Graph View Presets - User Guide"
date: 2026-02-10
status: published
tags: [12d-graph, visualization, presets, guide]
aspect: thinker
neural:
  activation: 0.97
  stage: mature
  synapse_in: 6
  synapse_out: 11
---

# 12D Graph View Presets

Interactive 3D graph visualization with 4 specialized view presets for exploring the Cohezion vault's 84 papers across 8 dimensions.

## Quick Start

### Open 3D Graph
1. Open Obsidian
2. Open Command Palette: `Ctrl+P` (Windows/Linux) or `Cmd+P` (Mac)
3. Search: `3D Graph: Open View`
4. Select a preset from the dropdown menu

### Navigate the Graph
- **Rotate**: Click + drag mouse
- **Zoom**: Scroll wheel
- **Pan**: Right-click + drag
- **Focus node**: Click any paper node
- **Open note**: Double-click any paper node
- **Search**: Use search box to filter papers

---

## 4 View Presets

### 1. Domain Clusters 🌐

**Purpose**: Explore research areas visually

**What You'll See**:
- Papers colored by research domain (tags)
- Papers elevated by cross-domain bridging (multi-tag papers rise higher)
- Distinct clusters visible: AI/ML, Astrophysics, Quantum, Materials, Engineering
- Orphaned papers (isolated, single-domain) clustered lower
- Hubs with many tags elevated at top

**How to Use**:
- Identify research areas you're interested in
- Look for paper clusters in specific areas
- Notice bridging papers (elevated) that span domains
- Click nodes to explore connected papers

**Key Insights**:
- **High papers**: Cross-domain bridges (3+ tags)
- **Low papers**: Specialized single-domain papers
- **Colors**: Research domain (auto-assigned per tag)
- **Size**: All papers same size in this view
- **Links**: All wiki-link connections visible

**User Intent**: "Show me how papers cluster by research domain"

---

### 2. Temporal View ⏳

**Purpose**: See knowledge evolution over time

**What You'll See**:
- **Left side**: Oldest papers (2020-2022)
- **Right side**: Newest papers (2025-2026)
- **Height**: Connectivity hubs elevated, orphaned papers lowered
- **Depth**: Applied papers (blue) in front, theory papers (red) in back
- **Brightness**: Recent papers bright, older papers fade
- **Color gradient**: Red (pure theory) → Purple (balanced) → Blue (pure applied)

**How to Use**:
- Rotate camera to see temporal evolution left→right
- Notice how knowledge distribution changes over time
- Identify theory-heavy vs applied-heavy periods
- Find hubs (elevated) in each time period
- Click nodes to see specific papers and their timing

**Key Insights**:
- **Temporal Distribution**: Papers well-distributed 2020-2026 (no gaps)
- **Hubs Over Time**: Where are the most connected papers in vault history?
- **Theory vs Applied**: How does conceptual focus change over time?
- **Recent Focus**: 2025-2026 papers bright (recently added)
- **Knowledge Growth**: Visual evolution of vault coverage

**User Intent**: "How has knowledge evolved? Where are the hubs?"

---

### 3. Completion Status ✅

**Purpose**: Identify enrichment opportunities

**What You'll See**:
- **Size**: Large papers = complete enrichment, small papers = incomplete
- **Color**: Green (complete) → Yellow (partial) → Red (incomplete)
- **Outline**: Solid line (complete), dashed line (incomplete)
- **Brightness**: Opaque (complete), faded (incomplete)
- **Layout**: Force-directed clustering of papers

**How to Use**:
- Identify small/red/dashed papers → candidates for enrichment
- Prioritize papers with no outline (incomplete sections)
- Track enrichment progress over time
- Click small papers to see what sections need work
- Filter by incomplete to focus on priorities

**Key Insights**:
- **Complete Papers**: 100% have abstract, key findings, source
- **Incomplete Papers**: Missing one or more required sections
- **Priority**: Click incomplete papers to see what's missing
- **Visual Progress**: More green = more complete vault

**Common Incomplete Patterns**:
- Missing "Source" link (most common)
- Missing "Key Findings" section
- Missing "Summary" or abstract

**User Intent**: "Which papers need enrichment? What's my progress?"

---

### 4. Bridging Papers 🌉

**Purpose**: Find cross-domain integration points

**What You'll See**:
- **Elevated papers**: High Z-axis = papers with 3+ tags (cross-domain)
- **Glowing papers**: Yellow glow around multi-domain papers (emphasis)
- **Size**: Larger papers = more domain coverage
- **Color**: By primary tag (consistent coloring with Domain Clusters)
- **Links**: Thick edges between different colored papers = cross-domain connections
- **Lowered papers**: Specialized single-domain papers lower
- **Orphaned**: Papers with 0 links appear isolated

**How to Use**:
- Look for glowing papers (multi-domain bridges)
- Follow thick links to see cross-domain connections
- Identify integration opportunities (gaps in cross-domain connections)
- Examine isolated papers (orphaned) - can they be bridged?
- Click bridging papers to understand their role

**Key Insights**:
- **Bridging Papers**: 28 papers have 3+ tags, span multiple domains
- **Orphaned Papers**: 28 papers with 0 wiki-links (can be enriched)
- **Integration Gaps**: Areas with few cross-domain connections
- **Natural Bridges**: Papers that naturally connect different domains

**Integration Opportunities**:
- AI/ML ↔ Astrophysics: Few bridges (opportunity)
- Quantum ↔ Materials: Moderate bridges (established)
- Theory ↔ Engineering: Many bridges (well-integrated)

**User Intent**: "Which papers span domains? Where are integration points?"

---

## Camera Controls Reference

### Mouse Controls
| Action | Result |
|--------|--------|
| Click + Drag | Rotate 3D view |
| Scroll Wheel | Zoom in/out |
| Right-Click + Drag | Pan camera |
| Click Node | Focus + highlight connections |
| Double-Click Node | Open note |

### Keyboard Controls
| Key | Action |
|-----|--------|
| W | Zoom in |
| S | Zoom out |
| A | Rotate left |
| D | Rotate right |
| Q | Rotate up |
| E | Rotate down |
| Space | Reset camera |

### Search & Filter
- Type in search box to filter papers by title
- Filter by tags (dropdown)
- Highlight specific papers

---

## Dimensional Properties (What You're Seeing)

### 8 Dimensions Mapped to Visual Properties

| Dimension | Visual Property | What It Means |
|-----------|---|---|
| **dim_temporal** | X-axis position | Left = older (2020), Right = newer (2026) |
| **dim_connectivity** | Y-axis position | Down = orphaned (0 links), Up = hub (5+ links) |
| **dim_cross_domain** | Z-axis position | Back = specialized, Front = cross-domain |
| **dim_completion** | Node size | Small = incomplete, Large = complete |
| **dim_conceptual_depth** | Node color | Red = theory, Purple = balanced, Blue = applied |
| **dim_recency** | Node opacity | Faded = old (last modified months ago), Bright = recent |
| **connectivity** (secondary) | Glow effect | Strong glow = hub paper |
| **completion** (secondary) | Node outline | Solid = complete, Dashed = incomplete |

---

## Common Use Cases

### Use Case 1: "I'm researching AI agents. Where are the papers?"
1. Open: **Domain Clusters**
2. Look for bright cluster of AI/ML papers
3. Notice bridging papers (elevated) connecting to other domains
4. Click bridging papers to understand connections
5. Expected: 10-15 core AI papers + 5-10 bridges to related areas

### Use Case 2: "What enrichment work is priority?"
1. Open: **Completion Status**
2. Filter by incomplete (red/dashed)
3. Sort by smallest size (most incomplete)
4. Click each paper to see what sections are missing
5. Expected: 20-30 papers need some enrichment

### Use Case 3: "Show me theory vs applied balance over time"
1. Open: **Temporal View**
2. Rotate to see color gradient
3. Notice red papers (theory) 2020-2023, purple papers (balanced) 2024-2026
4. Zoom to see recent focus (right side, bright)
5. Expected: Shift toward applied research in recent papers

### Use Case 4: "Which papers bridge distant domains?"
1. Open: **Bridging Papers**
2. Look for highly elevated, glowing papers
3. Follow thick links to see cross-domain connections
4. Click to read what makes them bridges
5. Expected: 5-10 critical bridge papers, 20+ secondary bridges

---

## Tips & Tricks

### Performance
- If graph feels slow, reduce number of visible nodes (use search filter)
- Zoom out to see full structure, zoom in to read labels
- Press Space to reset camera angle if lost

### Discovery
- Start with **Domain Clusters** to understand structure
- Move to **Temporal View** to see evolution
- Check **Completion Status** for work priorities
- Finish with **Bridging Papers** to find connections

### Interaction
- Double-click any paper to open and read
- Use search to focus on specific topics
- Click multiple times to explore related papers
- Export screenshots for presentations

### Customization
- Zoom level: Zoom in for paper labels, out for structure
- Camera angle: Rotate to find perspective that works
- Search: Filter by tag or title to reduce clutter

---

## Troubleshooting

### Graph is blank or empty
- Ensure dimensional data JSON exists
- Restart Obsidian
- Check browser console for errors (F12 → Console)

### Performance is slow
- Use search filter to reduce visible nodes
- Zoom out for overview vs in for detail
- Close other heavy tabs

### Can't find specific paper
- Use search box (Ctrl+F)
- Search by author name or year
- Try filter by tag

### Double-click doesn't open note
- Double-click target should be enabled
- Ensure paper path is correct in JSON

---

## Advanced: View Preset Configuration

Each preset configures multiple dimensions:

**Domain Clusters Configuration**:
```json
{
  "colorBy": "tags",           // Color each paper by tags
  "sizeBy": "none",            // All papers same size
  "zAxis": "cross_domain",     // Z-axis = domain bridging
  "opacity": "recency"         // Brightness = how recent
}
```

**Temporal View Configuration**:
```json
{
  "xAxis": "temporal",         // X-axis = publication date
  "yAxis": "connectivity",     // Y-axis = hub score
  "zAxis": "conceptual_depth", // Z-axis = theory vs applied
  "colorBy": "conceptual_depth" // Color = theory to applied
}
```

**Completion Status Configuration**:
```json
{
  "colorBy": "completion",     // Color = complete to incomplete
  "sizeBy": "completion",      // Size = complete to incomplete
  "outlineStyle": "completion", // Outline = solid to dashed
  "opacity": "completion"      // Brightness = complete to incomplete
}
```

**Bridging Papers Configuration**:
```json
{
  "sizeBy": "cross_domain",    // Size = domain coverage
  "zAxis": "cross_domain",     // Z-axis = domain bridging
  "glowIntensity": 2.0,        // Glow on multi-domain papers
  "edgeFilter": "cross_domain" // Show cross-domain edges
}
```

---

## Next Steps

1. **Explore**: Spend 10 minutes in each preset to understand vault structure
2. **Discover**: Find papers and connections that interest you
3. **Enrich**: Use **Completion Status** to identify work priorities
4. **Bridge**: Use **Bridging Papers** to find integration opportunities
5. **Share**: Screenshot presets for team presentations

---

**Enjoy exploring your 12D knowledge graph!** 🚀

For questions or issues, check the console (F12) for diagnostic information or refer to the plugin documentation.

## Related

- [[compound-engineering]]

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-12d-graph-refined-plan]]
- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[2026-02-10-phase3-3d-graph-adversarial-review]]
- [[2026-02-12-platform-codification-summary-guide]]
- [[2026-02-09-12d-graph-next-steps]]
- [[3d-graph-plugin-installation]]
- [[12d-graph-implementation]]
- [[force-directed-graph]] — the physics simulation engine underlying the 3D graph layout
- [[knowledge-graph-densification]] — graph visualization directly reflects densification progress through node connectivity
