# SKILL: PERSISTENT_UNIVERSE_PRIME

## DOMAIN EXPERTISE

Expert in persistent AI simulation with cloud synchronization and bidirectional state management. Specializes in designing systems where simulation continues even when local compute pauses, maintaining "institutional intelligence" through stateful AI memory.

## KEY TEXTS & CONCEPTS

- **Stateful AI**: Agents remember and learn from ongoing interactions
- **Real-is-Sim**: Persistent digital twin bridging simulation and reality
- **Bidirectional Sync**: Changes reflect automatically in all systems
- **Multi-Agent Coordination**: Specialized sub-agents with clean contexts
- **Institutional Intelligence**: Compounding memory advantage

## INSTRUCTION

### 1. Design for Persistence
```python
class PersistentUniverse:
    def __init__(self, db: SurrealClient, cloud_sync: CloudSync):
        self.db = db
        self.cloud = cloud_sync
        self.state_version = 0
    
    async def checkpoint(self):
        """Save current state for recovery."""
        state = await self.get_full_state()
        await self.db.store_checkpoint(state, self.state_version)
        await self.cloud.sync_checkpoint(state, self.state_version)
        self.state_version += 1
```

### 2. Bidirectional Cloud Sync
```python
class CloudSync:
    async def sync_bidirectional(self):
        """Merge local and cloud states."""
        local_state = await self.get_local_state()
        cloud_state = await self.get_cloud_state()
        
        # Conflict resolution (last-write-wins or merge)
        merged = self.merge_states(local_state, cloud_state)
        
        await self.update_local(merged)
        await self.update_cloud(merged)
```

### 3. State Recovery
```python
async def resume_simulation(self):
    """Resume from last checkpoint."""
    latest = await self.db.get_latest_checkpoint()
    if latest is None:
        latest = await self.cloud.get_latest_checkpoint()
    
    await self.restore_state(latest)
    return latest.version
```

### 4. Event Bus for Real-Time Updates
```python
class EventBus:
    async def publish(self, event: SimulationEvent):
        # Local handlers
        await self.local_handlers.process(event)
        # Cloud sync
        await self.cloud.queue_event(event)
    
    async def subscribe(self, handler, event_type):
        self.local_handlers.register(handler, event_type)
```

## VERSION
v1.0

## SEE ALSO
- GATEWAY_ARCHITECTURE_PRIME.md - Gateway 4 uses this
- OBSERVABLE_AI_PRIME.md - Observability integration
- PHYSICS_INFORMED_PREDICTION_PRIME.md - State prediction
