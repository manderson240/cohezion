# SECURITY FIX 002: Subprocess Security Hardening

**Phase**: 1  
**Security Risk Level**: Critical  
**Epic**: SEC-002  
**Story**: SEC-007  
**PRD Section**: 4.1 (System Integration Security)

## Executive Summary

This document details the security hardening implemented to prevent subprocess hijacking attacks via PATH manipulation. The fix addresses a critical vulnerability where attackers could execute arbitrary code by modifying the PATH environment variable to hijack subprocess calls to `nvidia-smi`, `sensors`, and other system binaries.

## Threat Model

### Attack Vector: PATH Manipulation

**Vulnerability**: Original code used relative command names with `subprocess.run()`:

```python
# VULNERABLE - Uses PATH lookup
subprocess.run(["nvidia-smi", "--query-gpu=driver_version"])
```

**Attack Scenario**:
1. Attacker compromises environment or modifies PATH
2. Creates malicious `nvidia-smi` binary in `/tmp` or user directory
3. Modifies PATH: `export PATH=/tmp:$PATH`
4. Python process executes attacker's binary with its privileges
5. Arbitrary code execution achieved

**Impact**: Complete system compromise with Python process privileges

## Security Measures Implemented

### 1. Absolute Path Resolution

All subprocess calls now use absolute paths instead of relative lookups:

```python
# BEFORE (vulnerable)
subprocess.run(["nvidia-smi", ...])

# AFTER (secure)
runner = SecureSubprocessRunner(safe_paths={"nvidia-smi": "/usr/bin/nvidia-smi"})
runner.run(["nvidia-smi", ...])
```

**Key Features**:
- Configurable safe paths map command names to absolute paths
- Fallback to `which` only for standard system directories (`/usr/bin`, `/bin`, etc.)
- Rejects paths outside safe directories

### 2. Binary Validation

Each binary is validated before execution:

| Check | Requirement | Purpose |
|-------|-------------|---------|
| File exists | Must exist | Prevents execution of missing binaries |
| Regular file | Must not be directory/special | Prevents device file execution |
| Ownership | Must be owned by root (configurable) | Ensures system-controlled binaries |
| Permissions | Maximum 755 (configurable) | Prevents world-writable binaries |
| Symlinks | Rejected by default | Prevents symlink attacks |
| Hash | Optional verification | Detects binary modifications |

**Implementation**:
```python
result = runner.validate_binary(
    path,
    expected_hash="abc123...",  # Optional
)
if not result.is_valid:
    raise BinaryValidationError(result.errors)
```

### 3. Environment Sanitization

All subprocess calls execute with a minimal, sanitized environment:

**Removed Variables**:
- `LD_PRELOAD` - Prevents library injection
- `LD_AUDIT`, `LD_PROFILE` - Prevents audit library attacks
- `MALLOC_CHECK_`, `MALLOC_TRACE` - Prevents heap exploitation
- `PYTHONPATH`, `CLASSPATH` - Prevents module hijacking
- All user-controlled path variables

**Safe PATH**:
```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### 4. Timeout Protection

All subprocess calls enforce timeouts:

```python
result = runner.run(
    ["nvidia-smi", ...],
    timeout=10,  # Kill after 10 seconds
)
if result.timed_out:
    logger.warning("Security event: subprocess timeout")
```

## Files Modified

### New Files

1. **`src/cohezion/security/subprocess_utils.py`**
   - `SecureSubprocessRunner` - Main security class
   - `BinaryValidationResult` - Validation results
   - `SecureSubprocessResult` - Execution results
   - `BinaryValidationError` - Security exceptions

2. **`tests/security/test_subprocess_security.py`**
   - Comprehensive security test suite
   - 25+ test cases covering all attack vectors

3. **`docs/security/SECURITY_FIX_002.md`** (this file)
   - Security documentation
   - Migration guide
   - Runbook

### Modified Files

4. **`src/cohezion/compound/hardware_monitor_hardwaremonitor.py`**
   - Migrated to use `SecureSubprocessRunner`
   - All `subprocess.run()` calls now use absolute paths
   - Environment sanitization applied

## Usage Examples

### Basic Usage

```python
from cohezion.security.subprocess_utils import get_secure_runner

runner = get_secure_runner()
result = runner.run(
    ["nvidia-smi", "--query-gpu=temperature.gpu"],
    timeout=10,
)
```

### Custom Configuration

```python
from cohezion.security.subprocess_utils import SecureSubprocessRunner

runner = SecureSubprocessRunner(
    safe_paths={
        "custom-cmd": "/opt/app/bin/custom-cmd",
    },
    require_root_owned=True,
    allow_symlinks=False,
    max_permissions=0o755,
    timeout_seconds=30,
)
```

### Binary Availability Check

```python
if runner.check_binary_available("nvidia-smi"):
    result = runner.run(["nvidia-smi", ...])
else:
    logger.info("nvidia-smi not available, using fallback")
```

## Migration Guide

### Before (Vulnerable)

```python
import subprocess

# Vulnerable to PATH manipulation
result = subprocess.run(
    ["nvidia-smi", "--query-gpu=temp"],
    capture_output=True,
    text=True,
    timeout=10,
)
```

### After (Secure)

```python
from cohezion.security.subprocess_utils import get_secure_runner

runner = get_secure_runner()
result = runner.run(
    ["nvidia-smi", "--query-gpu=temp"],
    timeout=10,
)
```

## Security Runbook

### Incident Response: Subprocess Hijacking

**Detection**:
- Monitor logs for `BinaryValidationError` exceptions
- Alert on `timed_out=True` results
- Alert on validation failures

**Response**:
1. Check system PATH: `echo $PATH`
2. Verify binary locations: `which nvidia-smi`
3. Check binary ownership: `ls -la /usr/bin/nvidia-smi`
4. Review process tree: `pstree -p <pid>`
5. Check LD_PRELOAD: `echo $LD_PRELOAD`

**Recovery**:
1. Kill compromised processes
2. Remove malicious binaries from PATH directories
3. Restart services with clean environment
4. Audit for unauthorized modifications

### Compliance Verification

Run security tests:
```bash
pytest tests/security/test_subprocess_security.py -v
```

Expected: All tests pass

## Testing

### Unit Tests

```bash
# Run all subprocess security tests
pytest tests/security/test_subprocess_security.py -v

# Run with coverage
pytest tests/security/test_subprocess_security.py --cov=cohezion.security.subprocess_utils
```

### Test Coverage

| Category | Tests |
|----------|-------|
| Initialization | 3 |
| Binary Resolution | 4 |
| Binary Validation | 7 |
| Environment Sanitization | 4 |
| Secure Execution | 6 |
| Timeout Handling | 2 |
| Edge Cases | 3 |
| **Total** | **25+** |

### Integration Test

```python
# Test actual GPU monitoring
from cohezion.compound.hardware_monitor import HardwareMonitor

monitor = HardwareMonitor()
metrics = monitor.get_current_metrics()

# Verify no exceptions raised
assert metrics.cpu_temp_current > 0
assert metrics.gpu_temp_current > 0
```

## Compliance

### Requirements Satisfied

| PRD Section | Requirement | Status |
|-------------|-------------|--------|
| 4.1.1 | Absolute path resolution | ✅ |
| 4.1.2 | Binary validation | ✅ |
| 4.1.3 | Environment sanitization | ✅ |
| 4.1.4 | Timeout protection | ✅ |
| 4.1.5 | Security logging | ✅ |

### Security Standards

- ✅ OWASP Input Validation
- ✅ CIS Benchmarks - Process Execution
- ✅ NIST SP 800-53 - AC-3 (Access Enforcement)

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks)
- [NIST SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
- Python `subprocess` Security: https://docs.python.org/3/library/subprocess.html#security-considerations

## Future Work

- [ ] Integrate with vault for binary hash storage
- [ ] Add seccomp-bpf sandboxing
- [ ] Implement capability dropping
- [ ] Add Linux namespaces isolation
- [ ] Extend to all subprocess calls in codebase

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-02  
**Author**: Security Team  
**Approved By**: Security Architecture Board
