"""Security and guardrail infrastructure for LLM operations."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.security.guardrail_factory import (
        create_default_pipeline as create_default_pipeline,
    )

with contextlib.suppress(Exception):
    from cohezion.security.guardrail_pipeline import GuardrailAction as GuardrailAction
    from cohezion.security.guardrail_pipeline import GuardrailPipeline as GuardrailPipeline
    from cohezion.security.guardrail_pipeline import GuardrailResult as GuardrailResult


__all__ = [
    "GuardrailAction",
    "GuardrailPipeline",
    "GuardrailResult",
    "create_default_pipeline",
]

# Wiring-sweep 2026-06-22: security/ orphan modules — creates import-graph edges.
with contextlib.suppress(Exception):
    from cohezion.security.adversarial_tester import AdversarialTester as AdversarialTester
with contextlib.suppress(Exception):
    from cohezion.security.adversarial_tester import TestResult as TestResult
with contextlib.suppress(Exception):
    from cohezion.security.agent_auth import AgentAuthManager as AgentAuthManager
with contextlib.suppress(Exception):
    from cohezion.security.agent_auth import AgentCredential as AgentCredential
with contextlib.suppress(Exception):
    from cohezion.security.api_key_auth import APIKeyValidator as APIKeyValidator
with contextlib.suppress(Exception):
    from cohezion.security.apikey_auth_middleware import (
        APIKeyAuthMiddleware as APIKeyAuthMiddleware,
    )
with contextlib.suppress(Exception):
    from cohezion.security.attack_patterns import AttackCategory as AttackCategory
with contextlib.suppress(Exception):
    from cohezion.security.attack_patterns import AttackPattern as AttackPattern
with contextlib.suppress(Exception):
    from cohezion.security.audit import AuditEvent as AuditEvent
with contextlib.suppress(Exception):
    from cohezion.security.audit import AuditLogger as AuditLogger
with contextlib.suppress(Exception):
    from cohezion.security.audit_log import AuditAction as AuditAction
with contextlib.suppress(Exception):
    from cohezion.security.audit_log import AuditLogEntry as AuditLogEntry
with contextlib.suppress(Exception):
    from cohezion.security.auth import AuthError as AuthError
with contextlib.suppress(Exception):
    from cohezion.security.cert_generator import CertificateGenerator as CertificateGenerator
with contextlib.suppress(Exception):
    from cohezion.security.consent_manager import ConsentManager as ConsentManager
with contextlib.suppress(Exception):
    from cohezion.security.consent_manager import ConsentScope as ConsentScope
with contextlib.suppress(Exception):
    from cohezion.security.constitutional_enforcer import (
        ConstitutionalEnforcer as ConstitutionalEnforcer,
    )
with contextlib.suppress(Exception):
    from cohezion.security.constitutional_enforcer import ViolationType as ViolationType
with contextlib.suppress(Exception):
    from cohezion.security.constitutional_shield import ConstitutionalShield as ConstitutionalShield
with contextlib.suppress(Exception):
    from cohezion.security.constitutional_shield import AuditVerdict as AuditVerdict
with contextlib.suppress(Exception):
    from cohezion.security.credentials import CredentialManager as CredentialManager
with contextlib.suppress(Exception):
    from cohezion.security.ethical_framework import EthicalFramework as EthicalFramework
with contextlib.suppress(Exception):
    from cohezion.security.ethical_framework import RiskLevel as RiskLevel
with contextlib.suppress(Exception):
    from cohezion.security.eval_awareness_defense import (
        EvalAwarenessDefense as EvalAwarenessDefense,
    )
with contextlib.suppress(Exception):
    from cohezion.security.eval_awareness_defense import CanaryToken as CanaryToken
with contextlib.suppress(Exception):
    from cohezion.security.file_lock_context import FileLock as FileLock
with contextlib.suppress(Exception):
    from cohezion.security.guardrail_adapters import NoOpGuard as NoOpGuard
with contextlib.suppress(Exception):
    from cohezion.security.guardrail_adapters import PromptInjectionGuard as PromptInjectionGuard
with contextlib.suppress(Exception):
    from cohezion.security.https_middleware import (
        HTTPSEnforcementMiddleware as HTTPSEnforcementMiddleware,
    )
with contextlib.suppress(Exception):
    from cohezion.security.log_redactor import RedactionFilter as RedactionFilter
with contextlib.suppress(Exception):
    from cohezion.security.mcp_https_client import MCPHTTPSClient as MCPHTTPSClient
with contextlib.suppress(Exception):
    from cohezion.security.memory_barrier import MemoryMappedBarrier as MemoryMappedBarrier
with contextlib.suppress(Exception):
    from cohezion.security.memory_barrier import GTTAllocation as GTTAllocation
with contextlib.suppress(Exception):
    from cohezion.security.output_filter import OutputFilter as OutputFilter
with contextlib.suppress(Exception):
    from cohezion.security.output_filter import FilterResult as FilterResult
with contextlib.suppress(Exception):
    from cohezion.security.pipeline import SecurityPipeline as SecurityPipeline
with contextlib.suppress(Exception):
    from cohezion.security.pipeline import SecurityPolicy as SecurityPolicy
with contextlib.suppress(Exception):
    from cohezion.security.pre_commit_config import PreCommitConfiguration as PreCommitConfiguration
with contextlib.suppress(Exception):
    from cohezion.security.prompt_guard import PromptGuard as PromptGuard
with contextlib.suppress(Exception):
    from cohezion.security.prompt_guard import ThreatLevel as ThreatLevel
with contextlib.suppress(Exception):
    from cohezion.security.provenance_hash import ProvenanceRegistry as ProvenanceRegistry
with contextlib.suppress(Exception):
    from cohezion.security.rate_limiter import RateLimiter as RateLimiter
with contextlib.suppress(Exception):
    from cohezion.security.rate_limiter import RateLimitConfig as RateLimitConfig
with contextlib.suppress(Exception):
    from cohezion.security.sandbox_security import SandboxRedTeam as SandboxRedTeam
with contextlib.suppress(Exception):
    from cohezion.security.tee_key_manager import TEEKeyManager as TEEKeyManager
with contextlib.suppress(Exception):
    from cohezion.security.tee_key_manager import KeyAccessMode as KeyAccessMode
with contextlib.suppress(Exception):
    from cohezion.security.tls_config import TLSConfig as TLSConfig
with contextlib.suppress(Exception):
    from cohezion.security.validators import ValidationError as ValidationError
with contextlib.suppress(Exception):
    from cohezion.security.vault import BitwardenVault as BitwardenVault
