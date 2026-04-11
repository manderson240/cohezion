# Test-Driven Integration Pattern

## Overview

Integrate new systems with existing infrastructure using the **Test-Driven Integration** pattern:
1. **First**: Write tests that define exactly how systems connect
2. **Then**: Create adapter layer to translate between interfaces
3. **Finally**: Implement adapters to make tests pass

This ensures:
- **Clear contracts** between systems
- **No breaking changes** to existing code
- **Testable integration** from day one
- **Living documentation** (tests are the spec)

---

## When to Use

Use this pattern when:
- Integrating new system with existing infrastructure
- Multiple systems need to communicate
- Interface boundaries are unclear
- Risk of breaking existing functionality
- Need to maintain backward compatibility

**Examples**:
- Adding circuit breakers to existing router
- Integrating proactive warming with model pools
- Connecting event system to existing logging
- Persisting patterns to existing vault

---

## The Pattern

### Step 1: Write Integration Tests First

```python
# tests/compound/test_dynamic_system_integration.py

class TestCircuitBreakerIntegration:
    """Define EXACTLY how circuit breakers integrate with router."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_in_router(self, router):
        """Circuit breaker OPEN → router skips backend."""
        # Given: GPU_ROCM circuit is OPEN
        # When: Router selects backend
        # Then: Should skip GPU_ROCM, select alternative
        
        circuit_breaker.open(BackendType.GPU_ROCM)
        backend = router.select_backend()
        
        assert backend != BackendType.GPU_ROCM
```

**Key**: Tests define the contract. Implementation must satisfy tests.

---

### Step 2: Create Adapter Classes

```python
# src/cohezion/compound/adapters.py

class CircuitBreakerRouterAdapter:
    """Adapts circuit breakers to existing router."""
    
    def __init__(self, router, circuit_breaker):
        self.router = router
        self.circuit = circuit_breaker
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Wire events between systems."""
        self.circuit.on_open(self._on_circuit_opened)
        self.circuit.on_close(self._on_circuit_closed)
    
    async def _on_circuit_opened(self, backend):
        """Mark backend unavailable in router."""
        self.router.mark_unavailable(backend)
    
    def is_available(self, backend) -> bool:
        """Check both circuit and router status."""
        if not self.circuit.can_execute(backend):
            return False
        return self.router.is_available(backend)
```

**Key**: Adapter is the only place systems touch. Decouples them.

---

### Step 3: Implement to Pass Tests

```python
# Make the test pass

async def test_circuit_breaker_blocks_in_router(self, router):
    # Setup
    adapter = CircuitBreakerRouterAdapter(router, circuit_breaker)
    
    # Execute
    circuit_breaker.record_failure(BackendType.GPU_ROCM)
    circuit_breaker.record_failure(BackendType.GPU_ROCM)
    circuit_breaker.record_failure(BackendType.GPU_ROCM)
    circuit_breaker.record_failure(BackendType.GPU_ROCM)
    circuit_breaker.record_failure(BackendType.GPU_ROCM)
    # Circuit now OPEN
    
    # Verify
    assert not adapter.is_available(BackendType.GPU_ROCM)
```

**Key**: Green test = correct integration.

---

## Complete Example

### Integration: Circuit Breakers + Router

**Test First**:
```python
class TestCircuitBreakerIntegration:
    @pytest_asyncio.fixture
    async def adapter(self, router, circuit_breaker):
        return CircuitBreakerRouterAdapter(router, circuit_breaker)
    
    @pytest.mark.asyncio
    async def test_blocks_when_open(self, adapter):
        """Router respects circuit breaker."""
        # Given: Circuit open
        adapter.circuit.open(BackendType.GPU_ROCM)
        
        # Then: Backend unavailable
        assert not adapter.is_available(BackendType.GPU_ROCM)
    
    @pytest.mark.asyncio
    async def test_recovers_when_closed(self, adapter):
        """Router restores when circuit closes."""
        # Given: Was open, now closed
        adapter.circuit.open(BackendType.GPU_ROCM)
        adapter.circuit.close(BackendType.GPU_ROCM)
        
        # Then: Backend available
        assert adapter.is_available(BackendType.GPU_ROCM)
```

**Adapter Implementation**:
```python
class CircuitBreakerRouterAdapter:
    def __init__(self, router, circuit):
        self.router = router
        self.circuit = circuit
        self._wire_events()
    
    def _wire_events(self):
        """Connect circuit events to router updates."""
        self.circuit.register_event(
            CircuitEvent.OPENED,
            self._on_opened
        )
        self.circuit.register_event(
            CircuitEvent.CLOSED,
            self._on_closed
        )
    
    async def _on_opened(self, backend):
        """Circuit opened → mark backend unavailable."""
        self.router.mark_unavailable(backend)
        logger.warning(f"Circuit opened for {backend}, routing around")
    
    async def _on_closed(self, backend):
        """Circuit closed → restore backend."""
        self.router.mark_available(backend)
        logger.info(f"Circuit closed for {backend}, restoring traffic")
    
    def is_available(self, backend) -> bool:
        """Check both circuit breaker and router."""
        # Circuit breaker overrides router
        if not self.circuit.can_execute(backend):
            return False
        return self.router.is_available(backend)
```

**Usage**:
```python
# Create integrated system
adapter = CircuitBreakerRouterAdapter(
    router=ComputeBackendRouter.get_default(),
    circuit=ProactiveReactiveEngine(mcp_client)
)

# Use transparently
if adapter.is_available(BackendType.GPU_VULKAN):
    return route_to_gpu()
else:
    return route_to_npu()  # Automatic fallback
```

---

## Integration Checklist

### Before Integration
- [ ] Understand existing system interface
- [ ] Understand new system interface
- [ ] Define integration contract (what should happen)

### During Integration
- [ ] Write tests defining the contract
- [ ] Create adapter class(es)
- [ ] Wire event handlers
- [ ] Make tests pass

### After Integration
- [ ] Verify no breaking changes to existing system
- [ ] Verify new system works standalone
- [ ] Document adapter interface
- [ ] Monitor integration health

---

## Benefits

### Traditional Integration
```
System A --calls--> System B
     ↓                ↓
  Tight coupling   Breaking changes
```

### Test-Driven Adapter Integration
```
System A --adapter--> System B
     ↓                   ↓
  Independent        Independent
     ↓                   ↓
  Change A without    Change B without
  breaking B            breaking A
```

**Advantages**:
- ✅ Clear contracts (tests define interface)
- ✅ No breaking changes (adapter isolates)
- ✅ Testable (tests verify integration)
- ✅ Documented (tests are living docs)
- ✅ Reversible (remove adapter to unwind)

---

## Common Patterns

### Pattern 1: Event Wiring

```python
class Adapter:
    def __init__(self, system_a, system_b):
        # Wire events from A to B
        system_a.on_event(
            Event.Type,
            lambda data: system_b.handle(data)
        )
```

**Use**: When systems communicate via events

---

### Pattern 2: Status Translation

```python
class Adapter:
    def get_status(self) -> Status:
        """Translate system A status to system B format."""
        a_status = self.system_a.get_status()
        return Status(
            available=a_status.is_up,
            latency=a_status.response_time
        )
```

**Use**: When systems have different status formats

---

### Pattern 3: Fallback Chain

```python
class Adapter:
    def execute(self, task):
        """Try primary, fallback to backup."""
        try:
            return self.primary.execute(task)
        except UnavailableError:
            return self.backup.execute(task)
```

**Use**: When one system can degrade to another

---

## Testing Strategies

### Strategy 1: Mock External System

```python
@pytest.mark.asyncio
async def test_adapter_handles_failure():
    """Test adapter when external system fails."""
    # Mock external system
    external = Mock()
    external.call.side_effect = ConnectionError()
    
    adapter = Adapter(external, system)
    
    # Should handle gracefully
    result = await adapter.call()
    assert result.fallback_used
```

### Strategy 2: Test Real Integration

```python
@pytest.mark.integration
async def test_real_integration():
    """Test with real systems (slower but thorough)."""
    real_a = SystemA()
    real_b = SystemB()
    
    adapter = Adapter(real_a, real_b)
    
    # Test actual integration
    result = await adapter.execute(task)
    assert result.success
```

### Strategy 3: Property-Based

```python
@pytest.mark.parametrize("failure_count", [1, 3, 5, 10])
async def test_opens_after_n_failures(failure_count):
    """Circuit opens after N failures."""
    adapter = create_adapter()
    
    for _ in range(failure_count):
        adapter.record_failure()
    
    expected_open = failure_count >= 5
    assert adapter.is_open() == expected_open
```

---

## Anti-Patterns

### ❌ Don't: Direct Coupling

```python
# BAD: System A directly calls System B
class SystemA:
    def execute(self):
        return system_b.call()  # Tight coupling!
```

### ✅ Do: Adapter Decoupling

```python
# GOOD: Adapter mediates
class Adapter:
    def __init__(self, system_b):
        self.b = system_b
    
    def execute(self):
        return self.b.call()

class SystemA:
    def __init__(self, adapter):
        self.adapter = adapter
    
    def execute(self):
        return self.adapter.execute()  # Decoupled
```

---

### ❌ Don't: Complex Integration Tests

```python
# BAD: Tests too complex, unclear what's being tested
async def test_everything():
    system = create_full_system()
    result = await system.execute()
    assert result.success
    assert result.metrics.latency < 100
    assert result.circuit_breaker.state == "closed"
    assert result.pool.warmed == True
    # Too much!
```

### ✅ Do: Focused Integration Tests

```python
# GOOD: One concept per test
async def test_circuit_opens_after_failures():
    """Just circuit behavior."""
    circuit = CircuitBreaker(threshold=5)
    
    for _ in range(5):
        circuit.record_failure()
    
    assert circuit.state == "open"

async def test_router_respects_circuit():
    """Just router + circuit integration."""
    adapter = CircuitRouterAdapter(router, circuit)
    circuit.open(BackendType.GPU)
    
    assert adapter.is_available(BackendType.GPU) == False
```

---

## References

- **Pattern**: Adapter Pattern (GoF)
- **Approach**: Test-Driven Development (TDD)
- **Testing**: Integration Testing Pyramid

**Implementation**:
- `tests/compound/test_dynamic_system_integration.py` - Example tests
- `src/cohezion/compound/dynamic_system_integration.py` - Example adapters

---

**Version**: 1.0
**Last Updated**: 2026-04-10
**Pattern Type**: Integration Architecture
