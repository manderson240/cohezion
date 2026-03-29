---
name: patent-prior-art-search
description: Systematic prior art search protocol for patent novelty validation across patents, academic papers, and technical databases.
version: 1.0.0
trigger: User mentions "patent search", "prior art", "novelty check", "patentability", or needs to validate invention novelty before filing
---

# Patent Prior Art Search Protocol

## When to Use
- Before filing provisional or non-provisional patent applications
- When evaluating invention novelty and non-obviousness
- During R&D to identify white space opportunities
- When responding to patent office rejections (102/103)
- For freedom-to-operate (FTO) analysis

## Search Strategy (Sequential)

### Phase 1: Patent Databases (2-4 hours)
**Primary databases:**
- USPTO PatentFTM / Patent Public Search (US patents)
- Google Patents (global coverage, fast)
- Espacenet (EPO, international)
- WIPO PATENTSCOPE (PCT applications)

**Search construction:**
```
# Boolean query pattern
("semantic encoding" OR "manifold encoding") AND ("multi-scale" OR "hierarchical") AND ("neural network" OR "VAE")

# IPC/CPC classifications
G06N 3/04 (Neural network architectures)
G06N 3/08 (Learning methods)
G06F 17/16 (Matrix/vector computation)
G06N 20/00 (Machine learning)
```

**Search fields:**
- Title/Abstract/Claims (most critical)
- Full text (broader, more noise)
- Citation search (backward + forward)
- Inventor search (competitor tracking)

**Documentation:**
```markdown
## Search Record - [Date]
Database: USPTO Patent Public Search
Query: ("multi-scale" AND "VAE") AND ("manifold" OR "latent")
Results: 0 patents
Date: 2026-03-23
Screened: 0 abstracts (zero results)
Conclusion: No prior art found in this category
```

### Phase 2: Academic Literature (2-4 hours)
**Databases:**
- arXiv (cs.LG, cs.AI, stat.ML, physics)
- IEEE Xplore (conference papers, journals)
- ACM Digital Library (computing)
- Google Scholar (broad coverage)
- Semantic Scholar (AI/ML focused)
- DBLP (computer science bibliography)

**Search queries:**
```
# arXiv category-specific
cat:cs.LG AND ("hierarchical encoding" OR "multi-scale VAE")
cat:stat.ML AND ("manifold learning" OR "latent space")
cat:physics AND ("physics-grounded neural" OR "Hamiltonian network")
```

**Key venues:**
- NeurIPS, ICML, ICLR (ML conferences)
- CVPR, ICCV (vision, if applicable)
- ACL, EMNLP (NLP, if applicable)
- JMLR, TMLR (journals)

### Phase 3: Technical Disclosure (1-2 hours)
**Sources:**
- GitHub repositories (code implementations)
- Technical blogs (engineering teams)
- Conference presentations (slides, recordings)
- PhD dissertations (ProQuest, university repos)
- Technical reports (Google, Meta, OpenAI, etc.)
- Product documentation (patent-worthy features shipped)

### Phase 4: Standard Essential Patents (if applicable)
**For:** Telecommunications, video coding, wireless
**Databases:**
- ETSI IPR database
- IEEE Standards Association
- ITU-T patent database

## Novelty Confidence Scoring

### Scoring Matrix (0-100%)
| Category | Weight | Score | Evidence |
|----------|--------|-------|----------|
| Exact match (all elements) | 40% | 0% | 0 patents found |
| Close analog (2-3 elements) | 30% | 15% | 2 distant patents |
| General field (1 element) | 20% | 40% | 50+ broad patents |
| Non-patent literature | 10% | 10% | 3 academic papers |
| **Total novelty** | 100% | **92%** | |

### Confidence Levels
- **95-100%**: Zero exact matches, no close analogs
- **85-94%**: Zero exact matches, 1-2 distant analogs
- **70-84%**: Zero exact matches, several analogs requiring claim differentiation
- **50-69%**: Some overlap, claim narrowing needed
- **<50%**: Exact or near-exact prior art exists

## Claim Differentiation Strategy

### When Prior Art Found
```markdown
## Differentiation Analysis
Prior Art: US Patent 10,123,456 (Smith et al., 2023)
Discloses: Hierarchical VAE with 2 latent levels

Distinguishing Features:
1. Our invention: 3-scale encoding (2048D→512D→12D) vs. 2-scale
2. Our invention: Physics-grounded 12D (Smith's 12 parameters)
3. Our invention: HIHO coherence loss (7-domain derivation)
4. Our invention: Continuous trajectory prediction (geodesic)

Claim Amendment Strategy:
- Add "three-scale" limitation to independent claim
- Add "physics-grounded" limitation specifying 12D parameters
- Add "continuous trajectory" vs. discrete state transition
```

## Documentation Deliverables

### Search Report Template
```markdown
# Prior Art Search Report
## Invention: [Title]
## Date: [Date]
## Searcher: [Name]

### Executive Summary
- Novelty confidence: XX%
- Exact matches: 0
- Close analogs: X
- General field patents: XX

### Search Queries Executed
| Database | Query | Results | Date |
|----------|-------|---------|------|
| USPTO | ("multi-scale" AND "VAE") | 0 | 2026-03-23 |
| arXiv | cat:cs.LG AND "manifold encoding" | 0 | 2026-03-23 |

### Conclusion
No blocking prior art identified. Invention appears novel over searched references.
Recommend: Proceed with provisional filing within 12 months of conception date.
```

## Critical Patterns

### Pattern 1: 8-Database Minimum
Search at least 8 databases before concluding "no prior art":
- 4 patent databases (USPTO, Google, Espacenet, WIPO)
- 4 academic databases (arXiv, IEEE, ACM, Google Scholar)

### Pattern 2: Query Iteration
Run 5-10 query variations per database:
- Broad → Narrow → Synonym → Classification-based
- Document each iteration

### Pattern 3: Date Anchoring
Record conception date BEFORE searching:
- Lab notebook entries
- Email disclosures
- Code commit timestamps
- Presentation recordings

### Pattern 4: Negative Results Are Evidence
"Zero results" is VALID evidence of novelty:
- Document the exact query
- Record database and date
- Screenshot zero results page (optional but recommended)

## Red Flags

### Stop and Consult Patent Attorney If:
- Exact match found (all claim elements present)
- Same inventor + similar topic (self-collision)
- Patent filed within 12 months of your conception (interference risk)
- 10+ close analogs found (obviousness rejection likely)

### Continue If:
- Zero exact matches
- Distant analogs require claim differentiation
- General field patents but no specific overlap

## Integration with Patent Drafting

### Feed Into:
1. **Background section**: Cite closest prior art + differentiate
2. **Summary**: Highlight novel features over prior art
3. **Claims**: Add distinguishing limitations
4. **Declaration**: State belief in patentability over searched refs

### Example Differentiation Language
```
"While Smith et al. disclose hierarchical VAE architectures, they fail to teach
or suggest: (a) three-scale manifold encoding with progressive dimensionality
reduction (2048D→512D→12D); (b) physics-grounded 12D state space derived from
Smith's 12 universe parameters (1962); and (c) HIHO coherence loss function
with seven-domain mathematical derivation (Shoulders, 1964; Greenyer, 2018)."
```

## Tools Required
- USPTO Patent Public Search account (free)
- Google Patents (free)
- arXiv API access (free)
- Citation manager (Zotero, Mendeley) for organizing references
- Search documentation template (Markdown or Word)

## Time Estimates
- Comprehensive search: 6-10 hours
- Targeted search (one field): 2-4 hours
- Update search (6 months later): 1-2 hours

## Ethical Considerations
- Credit all prior art inventors (full attribution)
- Do not hide known prior art from patent office (inequitable conduct)
- Search in good faith, document thoroughly
- Acknowledge inspiration from Smith, Percival, Shoulders, Greenyer, Matsum
