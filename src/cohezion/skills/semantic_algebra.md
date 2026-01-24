# SKILL: SEMANTIC_ALGEBRA_PRIME

## DOMAIN EXPERTISE

Expert in performing mathematical operations on semantic concepts in continuous latent space. Specializes in vector arithmetic on thought representations, enabling cross-domain bridging, conceptual analogy discovery, and semantic interpolation.

## KEY TEXTS & CONCEPTS

- **Semantic Addition**: base + direction = new concept
- **Semantic Direction**: to_concept - from_concept = transformation vector
- **Cross-Domain Bridge**: concept + domain_shift = analogous concept
- **Cosine Similarity**: Measure conceptual distance in thought-space
- **Word2Vec Analogy**: king - man + woman = queen pattern

## INSTRUCTION

### 1. Encode Concepts to Vectors
```python
from cohezion.flume import FlumeEncoder

encoder = FlumeEncoder()
z_quantum = encoder.encode("quantum mechanics")
z_biology = encoder.encode("cellular biology")
```

### 2. Compute Semantic Directions
```python
# Direction from physics to biology
direction = encoder.semantic_direction("physics", "biology")
# direction represents the conceptual shift
```

### 3. Apply Cross-Domain Bridging
```python
# Transform "electron" from physics domain to biology domain
bridged = encoder.cross_domain_bridge(
    concept_a="electron",
    domain_a_example="physics",
    domain_b_example="biology"
)
# Returns analog concept like "ion" or "neuron signal"
```

### 4. Semantic Arithmetic
```python
# Novel concept generation
z_new = encoder.semantic_add(
    base="machine learning",
    direction="quantum",
    scale=0.5
)
decoded = encoder.decode(z_new)
# Creates hybrid concept
```

### 5. Measure Similarity
```python
sim = encoder.similarity("photosynthesis", "solar panel")
# Returns value 0-1 indicating conceptual similarity
```

## VERSION
v1.0

## SEE ALSO
- FLUME_METHODOLOGY_PRIME.md - Underlying encoding
- GATEWAY_ARCHITECTURE_PRIME.md - Where this fits in architecture
- CROSS_MODAL_EMBEDDING_PRIME.md (future) - Multi-modal extension
