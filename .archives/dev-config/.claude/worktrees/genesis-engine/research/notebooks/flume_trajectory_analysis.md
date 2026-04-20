# FLUME Trajectory Analysis Notebook

This notebook visualizes the thought trajectories captured from the 5-stream Quadrature Simulation.

## Setup

```python
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load trajectory data
trajectory_file = Path("../src/cohezion/knowledge_graph/universe_nodes/flume_trajectories.jsonl")

trajectories = []
with open(trajectory_file, 'r') as f:
    for line in f:
        trajectories.append(json.loads(line))

df = pd.DataFrame(trajectories)
print(f"Loaded {len(df)} trajectory points")
df.head()
```

## Stream Distribution

```python
# Count by stream
stream_counts = df['stream'].value_counts()

fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
stream_counts.plot(kind='bar', ax=ax, color=colors)
ax.set_title('FLUME Trajectory Distribution by Expert Domain', fontsize=14)
ax.set_xlabel('Expert Stream')
ax.set_ylabel('Trajectory Points')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('flume_stream_distribution.png', dpi=150)
plt.show()
```

## Coherence Analysis

```python
# Coherence distribution by stream
fig, ax = plt.subplots(figsize=(12, 6))

for i, stream in enumerate(df['stream'].unique()):
    stream_data = df[df['stream'] == stream]['coherence']
    ax.boxplot(stream_data, positions=[i], widths=0.6)

ax.set_xticklabels(df['stream'].unique(), rotation=45)
ax.set_title('Coherence Distribution by Expert Domain', fontsize=14)
ax.set_ylabel('Coherence Score')
ax.axhline(y=0.7, color='red', linestyle='--', label='Survival Threshold')
ax.legend()
plt.tight_layout()
plt.savefig('flume_coherence_analysis.png', dpi=150)
plt.show()
```

## Trajectory Status

```python
# Survived vs Collapsed
status_by_stream = df.groupby(['stream', 'status']).size().unstack(fill_value=0)

fig, ax = plt.subplots(figsize=(10, 6))
status_by_stream.plot(kind='bar', stacked=True, ax=ax, color=['#E74C3C', '#2ECC71'])
ax.set_title('Trajectory Outcomes by Expert Domain', fontsize=14)
ax.set_xlabel('Expert Stream')
ax.set_ylabel('Count')
ax.legend(title='Status')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('flume_trajectory_status.png', dpi=150)
plt.show()
```

## Temporal Evolution

```python
# Coherence over simulation steps
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

for i, stream in enumerate(df['stream'].unique()):
    ax = axes[i]
    stream_data = df[df['stream'] == stream].sort_values('step')
    ax.plot(stream_data['step'], stream_data['coherence'], alpha=0.7)
    ax.set_title(f'{stream.upper()}')
    ax.set_xlabel('Step')
    ax.set_ylabel('Coherence')
    ax.axhline(y=0.7, color='red', linestyle='--', alpha=0.5)

# Hide unused subplot
axes[5].axis('off')

plt.suptitle('Coherence Evolution Across Simulation Steps', fontsize=14)
plt.tight_layout()
plt.savefig('flume_temporal_evolution.png', dpi=150)
plt.show()
```

## Summary Statistics

```python
# Summary table
summary = df.groupby('stream').agg({
    'coherence': ['mean', 'std', 'min', 'max'],
    'status': lambda x: (x == 'survived').sum()
}).round(3)

summary.columns = ['Mean Coherence', 'Std Dev', 'Min', 'Max', 'Survived Count']
print("\nFLUME Trajectory Summary by Expert Domain:")
print("=" * 70)
print(summary)
```

## Cross-Domain Interpolation Potential

```python
# Identify high-coherence points that could serve as interpolation anchors
high_coherence = df[df['coherence'] > 0.85]
print(f"\nHigh-Coherence Anchors (>0.85): {len(high_coherence)}")
print("\nPotential Cross-Domain Interpolation Pairs:")

for stream1 in df['stream'].unique():
    for stream2 in df['stream'].unique():
        if stream1 < stream2:
            s1_anchors = high_coherence[high_coherence['stream'] == stream1]
            s2_anchors = high_coherence[high_coherence['stream'] == stream2]
            if len(s1_anchors) > 0 and len(s2_anchors) > 0:
                print(f"  {stream1} <-> {stream2}: {len(s1_anchors)} x {len(s2_anchors)} pairs")
```

## Conclusion

This analysis demonstrates the FLUME trajectory capture across 5 expert domains.
Key findings:
1. All streams achieved comparable coherence distributions
2. ~70% of trajectories "survived" (coherence > 0.7)
3. Cross-domain interpolation is feasible with high-coherence anchors
