# Cloud Database Options Research
## Privacy-Preserving Free & Low-Cost Solutions

**Research Date:** February 2, 2026  
**Status:** Documentation Only - Implementation Deferred  
**Current Solution:** SurrealDB (local) + SQLite Fallback

---

## Executive Summary

For Cohezion's universe simulation data (12D/512D manifold trajectories, agent journeys, knowledge graphs), we need a database solution that:
1. Supports vector embeddings (512 dimensions)
2. Handles JSON/schemaless data flexibly
3. Provides privacy (self-hosted or encrypted)
4. Offers free or low-cost tiers
5. Enables synchronization between local and cloud

---

## Option 1: SurrealDB Cloud (Recommended for Future)

**Website:** https://surrealdb.com/cloud  
**Cost:** Free tier available (5GB storage, 1M requests/month)  
**Privacy:** Enterprise-grade encryption, EU data centers available  

### Pros:
- Native vector search support (exactly what we need for 512D embeddings)
- SurrealQL is already our query language
- Seamless migration from local SurrealDB
- Real-time sync capabilities
- ACID compliance

### Cons:
- Free tier limits may constrain large-scale universe simulations
- Requires internet connectivity (no offline mode)
- Vendor lock-in to SurrealDB ecosystem

### Privacy Features:
- End-to-end encryption at rest and in transit
- SOC 2 Type II compliance
- GDPR compliant
- Private network isolation available

### When to Migrate:
- When local storage exceeds 50GB
- When multi-device sync becomes critical
- When team collaboration features needed

---

## Option 2: Supabase (PostgreSQL + Vector Extension)

**Website:** https://supabase.com  
**Cost:** Generous free tier (500MB database, 2GB storage)  
**Privacy:** Self-hostable open source, or managed with encryption  

### Pros:
- PostgreSQL with pgvector extension (supports 512D vectors)
- Open source - can self-host for maximum privacy
- Real-time subscriptions
- Auth built-in
- Edge functions for serverless compute

### Cons:
- Requires schema migrations (more rigid than SurrealDB)
- Self-hosting requires DevOps expertise
- pgvector performance degrades at very high dimensions

### Privacy Features:
- Self-hosting option gives full data control
- Encryption at rest (managed version)
- Row-level security policies
- SOC 2 compliant

### Migration Path:
```python
# Conceptual migration from SurrealDB to PostgreSQL
# Would require: Schema translation, data export/import, query rewriting
```

---

## Option 3: ChromaDB (Vector-First)

**Website:** https://www.trychroma.com  
**Cost:** Free (open source), paid cloud coming  
**Privacy:** Fully self-hostable  

### Pros:
- Purpose-built for vector embeddings
- Excellent for semantic search on 512D data
- Embeddable (runs in-process)
- Simple API

### Cons:
- Not a general-purpose database (need separate DB for metadata)
- Limited query capabilities beyond vector search
- Newer project, less mature ecosystem

### Privacy:
- 100% self-hostable
- No cloud dependency required
- Data never leaves your infrastructure

### Use Case:
- Best as augmentation to existing DB, not replacement
- Could enhance SurrealDB with specialized vector ops

---

## Option 4: CockroachDB Serverless

**Website:** https://www.cockroachlabs.com  
**Cost:** 5GB free, then pay-per-use  
**Privacy:** Enterprise-grade, distributed SQL  

### Pros:
- Distributed SQL (excellent for multi-region)
- PostgreSQL compatible
- Automatic scaling
- Strong consistency

### Cons:
- No native vector support (would need pgvector)
- Complex for simple use cases
- Higher learning curve

### Privacy:
- Encryption in transit and at rest
- SOC 2 Type II
- HIPAA compliant options

---

## Option 5: Edge-First: Cloudflare D1 + Vectorize

**Website:** https://workers.cloudflare.com  
**Cost:** Very generous free tier  
**Privacy:** Edge-distributed, encrypted  

### Pros:
- Globally distributed (low latency)
- SQLite-compatible (D1)
- Vectorize for embeddings
- Serverless architecture

### Cons:
- Vendor lock-in to Cloudflare
- Limited query complexity
- Still in beta/early access for some features

### Privacy:
- Data processed at edge (close to user)
- Encryption standard
- No central data concentration

---

## Recommended Strategy

### Phase 1: Current (Local-First)
**Implementation:** ✅ Complete
- SurrealDB local instance
- SQLite fallback for offline
- Git-based knowledge graph backup

### Phase 2: Hybrid (Individual Users)
**Timeline:** When user count > 10
- SurrealDB Cloud free tier for sync
- Local SQLite remains primary (privacy)
- Cloud acts as backup and sync broker

### Phase 3: Scale (Team/Enterprise)
**Timeline:** When collaboration needed
- Self-hosted SurrealDB or Supabase
- Private network (VPN/Tailscale)
- Encrypted at rest and transit

### Phase 4: Federation (Distributed Universe)
**Timeline:** Advanced usage
- CockroachDB for global distribution
- Edge nodes (Cloudflare) for low-latency
- Federated knowledge graphs

---

## Data Synchronization Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL DEVICE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SurrealDB   │  │   SQLite     │  │   Knowledge      │  │
│  │  (Primary)   │◄─┤  (Fallback)  │  │   Graph (Git)    │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────┘  │
│         │                                                   │
│         │ Sync (encrypted)                                  │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │   Sync Queue │◄──────────────┐                          │
│  └──────┬───────┘              │                          │
└─────────┼──────────────────────┼──────────────────────────┘
          │                      │
          ▼                      │
┌─────────────────────────────────────────────────────────────┐
│                    CLOUD (Optional)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ SurrealDB    │  │  Object      │  │   Backup         │  │
│  │ Cloud /      │  │  Storage     │  │   Archive        │  │
│  │ Self-Hosted  │  │  (Encrypted) │  │   (Cold)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Security & Privacy Checklist

For any cloud migration:

- [ ] End-to-end encryption at rest
- [ ] TLS 1.3 in transit
- [ ] Private network/VPN capability
- [ ] Data residency options (EU, US, etc.)
- [ ] GDPR/CCPA compliance
- [ ] SOC 2 Type II certification
- [ ] Audit logging
- [ ] Row-level encryption for sensitive data
- [ ] Self-hosting option available
- [ ] Vendor lock-in mitigation strategy

---

## Decision Matrix

| Criteria | SurrealDB Cloud | Supabase | ChromaDB | CockroachDB | Cloudflare |
|----------|----------------|----------|----------|-------------|------------|
| Vector Support | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Free Tier | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Privacy | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Ease of Migration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Self-Hosting | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ |
| Maturity | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**Current Winner:** SurrealDB Cloud (when ready to migrate)  
**Privacy Winner:** Supabase (self-hosted) or ChromaDB

---

## Next Steps (Deferred)

1. **Monitor** local storage growth
2. **Benchmark** SurrealDB Cloud with test data
3. **Evaluate** privacy requirements with legal
4. **Plan** migration strategy with rollback option
5. **Implement** sync layer when threshold reached

---

**Note:** All implementations deferred until local storage threshold (50GB) or multi-user collaboration requirements emerge.
