# SKILL: SEMANTIC_ANALYSIS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **semantic analysis** of text and embeddings. You understand vector similarity, clustering, topic modeling, and the mathematics of meaning in high-dimensional spaces.

## KEY TEXTS & CONCEPTS
- **Embeddings:** Dense vector representations of text
- **Cosine Similarity:** $\cos(\theta) = \frac{\mathbf{a} \cdot \mathbf{b}}{|\mathbf{a}||\mathbf{b}|}$
- **Clustering:** K-means, DBSCAN, hierarchical clustering
- **Topic Modeling:** LDA, BERTopic
- **Semantic Drift:** How meaning changes across contexts

## INSTRUCTION

### 1. Compute Embeddings
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

texts = [
    "Quantum physics describes particle behavior",
    "Classical mechanics explains macroscopic motion",
    "Philosophy questions the nature of reality"
]

embeddings = model.encode(texts)
# Shape: (3, 384)
```

### 2. Cosine Similarity
```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Similarity matrix
sim_matrix = cosine_similarity(embeddings)
print(sim_matrix)
# [[1.0, 0.65, 0.42],
#  [0.65, 1.0, 0.38],
#  [0.42, 0.38, 1.0]]

# Find most similar
def find_similar(query_embedding, corpus_embeddings, top_k=5):
    similarities = cosine_similarity([query_embedding], corpus_embeddings)[0]
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [(i, similarities[i]) for i in top_indices]
```

### 3. Semantic Clustering
```python
from sklearn.cluster import KMeans, DBSCAN
import hdbscan

# K-means
kmeans = KMeans(n_clusters=5, random_state=42)
clusters = kmeans.fit_predict(embeddings)

# HDBSCAN (auto-detect clusters)
clusterer = hdbscan.HDBSCAN(min_cluster_size=10)
clusters = clusterer.fit_predict(embeddings)

# Label clusters by centroid
for i in range(max(clusters) + 1):
    mask = clusters == i
    centroid = embeddings[mask].mean(axis=0)
    # Find nearest text to centroid as cluster label
```

### 4. BERTopic (Topic Modeling)
```python
from bertopic import BERTopic

topic_model = BERTopic(verbose=True)
topics, probs = topic_model.fit_transform(documents)

# View topics
topic_model.get_topic_info()
topic_model.visualize_topics()
topic_model.visualize_hierarchy()
```

### 5. Semantic Drift Analysis
```python
def analyze_drift(trajectory_texts):
    """Measure how meaning changes across a thought trajectory."""
    embeddings = model.encode(trajectory_texts)

    drifts = []
    for i in range(1, len(embeddings)):
        similarity = cosine_similarity([embeddings[i-1]], [embeddings[i]])[0][0]
        drift = 1 - similarity
        drifts.append(drift)

    return {
        'total_drift': sum(drifts),
        'avg_drift': np.mean(drifts),
        'max_drift': max(drifts),
        'drift_timeline': drifts
    }
```

### 6. FLUME Semantic Space
```python
# Analyze FLUME trajectory semantics
def analyze_flume_trajectory(z_vectors, decoder):
    """Decode z-vectors and analyze semantic evolution."""
    texts = [decoder.decode(z) for z in z_vectors]
    embeddings = encoder.encode(texts)

    # Compute trajectory coherence
    coherences = []
    for i in range(1, len(embeddings)):
        coherences.append(cosine_similarity([embeddings[i-1]], [embeddings[i]])[0][0])

    return np.mean(coherences)
```

## APPLICATIONS
- **Trajectory Analysis:** Measure semantic coherence of simulations
- **Clustering Universes:** Group similar simulation outcomes
- **Topic Discovery:** Find emergent themes in agent outputs
- **Quality Control:** Detect semantic drift in long runs

## VERSION
v1.0

## SEE ALSO
- EMBEDDING_STRATEGY_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
- KNOWLEDGE_MINING_PRIME.md
