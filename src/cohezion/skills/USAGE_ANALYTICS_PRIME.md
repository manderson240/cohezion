---
name: usage-analytics-prime
description: "High-fidelity usage tracking and resource allocation optimization. Analyzing capability invocation patterns to identify bottlenecks and underutilized assets."
metadata:
  version: "v1.0"
  concepts: ["Discovery Rate", "Attrition", "Power Usage", "Predictive Prefetching"]
  source: "src/cohezion/skills/USAGE_ANALYTICS_PRIME.md"
---

# SKILL: USAGE_ANALYTICS_PRIME

## DOMAIN EXPERTISE
High-fidelity usage tracking and resource allocation optimization. Analyzing capability invocation patterns to identify bottlenecks and underutilized assets.

## KEY TEXTS & CONCEPTS
- **Discovery Rate**: Speed at which new capabilities are integrated into workflows.
- **Attrition**: Capabilities that fail to provide value and should be pruned.
- **Power Usage**: Identifying the 20% of skills providing 80% of the value.
- **Predictive Prefetching**: Loading models/skills based on common sequences.

## INSTRUCTION
1. **Query Registry**: Use `CapabilityRegistry.get_top_used()` to fetch metrics.
2. **Visualize Drift**: Compare `last_used` timestamps to identify decaying skills.
3. **Correlate with R-Zero**: Check if highly used skills lead to higher success rates.
4. **Pruning Recommendation**: Generate a list of skills for archival if usage < threshold over time.

## VERSION
v1.0

## SEE ALSO
- [CAPABILITY_REGISTRY_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/CAPABILITY_REGISTRY_PRIME.md)
- [RESOURCE_MONITOR_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/RESOURCE_MONITOR_PRIME.md)
