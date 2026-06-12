"""Tests for TraceMonad — monad laws, state threading, and >> operator."""


class TestMonadLaws:
    def test_left_identity(self):
        """unit(a, s).bind(f) == f(a, s)  — left identity law."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        def f(value, state):
            return TraceMonad(value * 2, state)

        s = TraceState(coherence=0.5)
        via_unit = TraceMonad.unit(5, s).bind(f)
        direct = f(5, s)
        assert via_unit.value == direct.value
        assert via_unit.state.coherence == direct.state.coherence

    def test_right_identity(self):
        """m.bind(unit) == m  — right identity law."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        m = TraceMonad(42, TraceState(coherence=0.7, phi=0.84, step_index=3))
        result = m.bind(lambda v, s: TraceMonad.unit(v, s))
        assert result.value == m.value
        assert result.state.coherence == m.state.coherence
        assert result.state.step_index == m.state.step_index

    def test_associativity(self):
        """m.bind(f).bind(g) == m.bind(lambda v, s: f(v, s).bind(g))  — associativity."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        def f(v, s):
            return TraceMonad(v + 1, TraceState(coherence=s.coherence + 0.1))

        def g(v, s):
            return TraceMonad(v * 2, TraceState(coherence=s.coherence + 0.05))

        m = TraceMonad.unit(0, TraceState(coherence=0.3))
        left = m.bind(f).bind(g)
        right = m.bind(lambda a, s: f(a, s).bind(g))
        assert left.value == right.value
        assert abs(left.state.coherence - right.state.coherence) < 1e-9

    def test_rshift_is_bind_alias(self):
        """>  operator produces identical result to bind."""
        from cohezion.evo.trace_monad import TraceMonad

        step = lambda v, s: TraceMonad(v + 10, s)
        m = TraceMonad.unit(5)
        assert (m >> step).value == m.bind(step).value

    def test_then_passes_state_unchanged(self):
        """then() applies a pure function — state is not touched."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        state = TraceState(coherence=0.6, phi=0.96, step_index=2)
        m = TraceMonad("hello", state)
        result = m.then(str.upper)
        assert result.value == "HELLO"
        assert result.state is state


class TestTraceState:
    def test_advance_increments_step_index(self):
        from cohezion.evo.trace_monad import TraceState

        s0 = TraceState(step_index=3)
        s1 = s0.advance(coherence=0.5, phi=1.0, modalities=["text"], latent=[0.5] * 16)
        assert s1.step_index == 4

    def test_advance_accumulates_modalities(self):
        from cohezion.evo.trace_monad import TraceState

        s0 = TraceState(modalities_used=("text",))
        s1 = s0.advance(coherence=0.5, phi=1.0, modalities=["audio"], latent=[])
        assert "text" in s1.modalities_used
        assert "audio" in s1.modalities_used

    def test_original_state_unchanged_after_advance(self):
        """TraceState is a frozen dataclass — advance() derives, never mutates."""
        from cohezion.evo.trace_monad import TraceState

        s0 = TraceState(coherence=0.3)
        s0.advance(coherence=0.7, phi=0.84, modalities=[], latent=[])
        assert s0.coherence == 0.3  # unchanged

    def test_advance_stores_latent_snapshot(self):
        from cohezion.evo.trace_monad import TraceState

        latent = [0.1 * i for i in range(16)]
        s0 = TraceState()
        s1 = s0.advance(coherence=0.5, phi=1.0, modalities=[], latent=latent)
        assert list(s1.latent_snapshot) == latent

    def test_advance_carries_latency_and_delta(self):
        from cohezion.evo.trace_monad import TraceState

        s0 = TraceState()
        s1 = s0.advance(coherence=0.5, phi=1.0, modalities=[], latent=[], latency_ms=42.5, latent_delta=0.003)
        assert s1.latency_ms == 42.5
        assert s1.latent_delta == 0.003


class TestMonadPipeline:
    def test_chained_steps_thread_coherence(self):
        """Two bind steps each advance coherence; final state reflects both."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        def step1(v, s):
            return TraceMonad(v, s.advance(coherence=0.4, phi=0.96, modalities=["text"], latent=[]))

        def step2(v, s):
            return TraceMonad(v, s.advance(coherence=0.5, phi=1.0, modalities=["audio"], latent=[]))

        result = TraceMonad.unit("task", TraceState()) >> step1 >> step2
        assert result.state.step_index == 2
        assert result.state.coherence == 0.5
        assert "text" in result.state.modalities_used
        assert "audio" in result.state.modalities_used

    def test_pipeline_value_passes_through_unchanged(self):
        """bind steps that only modify state leave the value untouched."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        state_advancer = lambda v, s: TraceMonad(v, s.advance(coherence=0.6, phi=0.96, modalities=[], latent=[]))
        result = TraceMonad.unit("sentinel-value", TraceState()) >> state_advancer >> state_advancer
        assert result.value == "sentinel-value"

    def test_three_step_pipeline_associativity(self):
        """((m >> f) >> g) >> h == m >> f >> g >> h  — chaining is associative."""
        from cohezion.evo.trace_monad import TraceMonad, TraceState

        inc = lambda v, s: TraceMonad(v + 1, s)
        m = TraceMonad.unit(0, TraceState())
        assert ((m >> inc) >> inc >> inc).value == (m >> inc >> inc >> inc).value
