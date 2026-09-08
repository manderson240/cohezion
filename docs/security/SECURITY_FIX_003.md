# SECURITY_FIX_003: Compression Bomb Protection

**Date:** March 1, 2026  
**Status:** ✅ Implemented  
**Severity:** Critical  
**Related:** Epic SEC-003, Story SEC-009  
**Reference:** PRD Section 5.3 (Resource Protection)

## Executive Summary

This security fix implements comprehensive protection against compression bomb (zip bomb) attacks in the Cohezion platform. Compression bombs are crafted payloads that decompress to exponentially larger sizes, potentially causing memory exhaustion and Denial of Service (DoS) conditions.

## Vulnerability Details

### Location
- **File:** `src/cohezion/compound/metrics_persistence.py`
- **Lines:** 634-644 (original vulnerable code)
- **Function:** `_compress_file()`

### Attack Vector
1. Attacker fills metrics with compressible garbage data
2. Creates extreme compression ratio (zip bomb pattern)
3. Decompression causes uncontrolled memory allocation
4. Results in Denial of Service due to memory exhaustion

### Original Vulnerable Code
```python
def _compress_file(self, file_path: Path) -> None:
    with open(file_path, "rb") as f_in:
        with gzip.open(compressed_path, "wb") as f_out:
            f_out.write(f_in.read())  # No size limits!
```

## Security Measures Implemented

### 1. Compression Limits

```python
MAX_COMPRESSION_RATIO = 100      # 100:1 maximum
MAX_COMPRESSED_SIZE = 100MB      # Maximum compressed file size
MAX_DECOMPRESSED_SIZE = 1GB      # Maximum decompressed size
CHUNK_SIZE = 64KB                # Streaming chunk size
```

### 2. Stream-Based Operations

All compression/decompression operations now use streaming with fixed-size chunks:
- Prevents loading entire file into memory
- Enables real-time ratio checking
- Supports early termination on limit violation

### 3. Bomb Detection

The system detects suspicious compression patterns:
- Ratios exceeding 100:1 trigger immediate abort
- Ratios exceeding 50:1 generate security alerts
- Repeated suspicious attempts from same source are tracked

### 4. Rate Limiting

```python
COMPRESSION_RATE_LIMIT = 60  # Operations per minute
```

- Prevents rapid-fire compression attempts
- Critical priority operations bypass rate limit
- Automatic retry-after calculation provided

### 5. Security Event Logging

All security events are logged with:
- Timestamp and severity
- Source file identification
- Detailed metrics (ratios, sizes)
- Alert escalation on repeated attempts

## Implementation

### New Module: `src/cohezion/security/compression_utils.py`

This module provides secure compression utilities:

```python
from cohezion.security.compression_utils import (
    CompressionSecurityError,
    CompressionBombDetected,
    DecompressionSizeExceeded,
    CompressionRateLimitExceeded,
    safe_compress_file,
    safe_decompress_file,
    safe_decompress_bytes,
    validate_compression_safety,
)
```

### Key Functions

#### `safe_compress_file()`
- **Purpose:** Compress file with security limits
- **Input:** Source path, destination path, compression level
- **Security:** Enforces ratio and size limits during compression
- **Error Handling:** Cleans up partial output on security violation

#### `safe_decompress_file()`
- **Purpose:** Decompress file with size limits
- **Input:** Source path, max size, chunk size
- **Security:** Stops decompression if size exceeds limit
- **Protection:** Prevents memory exhaustion from bomb payloads

#### `safe_decompress_bytes()`
- **Purpose:** Decompress in-memory bytes safely
- **Input:** Compressed bytes, max size
- **Security:** Same protections as file-based version

#### `validate_compression_safety()`
- **Purpose:** Validate compressed file before decompression
- **Input:** Compressed file path
- **Output:** Safety assessment with estimated sizes
- **Use Case:** Pre-flight checks for batch operations

## Changes to Existing Code

### `metrics_persistence.py`

All vulnerable locations updated:

1. **`_compress_file()`** - Now uses `safe_compress_file()`
2. **`_read_file()`** - Now uses `safe_decompress_file()`
3. **`load_latest_snapshot()`** - Now uses `safe_decompress_file()`
4. **`save_snapshot()`** - Now uses `safe_compress_file()`
5. **`get_stats()`** - Now uses secure decompression for ratio calculation

### Exception Handling

All compression operations now handle:
```python
except CompressionSecurityError as e:
    logger.error("Security error: %s (%s)", e.message, e.code)
    # Safe fallback behavior
```

## Security Event Types

| Event Type | Severity | Description |
|------------|----------|-------------|
| `suspicious_compression_ratio` | error | Compression ratio exceeds limit during compression |
| `suspicious_decompression_ratio` | error | Compression ratio exceeds limit during decompression |
| `suspicious_compression_validation` | error | Validation detects suspicious file |
| `decompression_size_exceeded` | error | Decompressed size exceeds 1GB limit |
| `compression_rate_limited` | warning | Rate limit exceeded |

## Testing

### Test Coverage

Comprehensive tests in `tests/security/test_compression_bomb.py`:

```bash
# Run compression security tests
uv run pytest tests/security/test_compression_bomb.py -v

# Run specific test categories
uv run pytest tests/security/test_compression_bomb.py::TestSafeCompressFile -v
uv run pytest tests/security/test_compression_bomb.py::TestSafeDecompressFile -v
uv run pytest tests/security/test_compression_bomb.py::TestCompressionRateLimiter -v
```

### Test Categories

1. **Unit Tests**
   - Normal compression/decompression
   - Bomb detection and blocking
   - Size limit enforcement
   - Rate limiting

2. **Integration Tests**
   - MetricsPersistence integration
   - Round-trip compression/decompression
   - Security event logging

3. **Edge Cases**
   - Empty files
   - Non-existent files
   - Corrupted data
   - Boundary conditions

## Configuration

### Security Limits (Hardcoded)

```python
# These are security-critical and should NOT be user-configurable
MAX_COMPRESSION_RATIO = 100       # Maximum 100:1
MAX_COMPRESSED_SIZE = 100MB       # 100 megabytes
MAX_DECOMPRESSED_SIZE = 1GB       # 1 gigabyte
COMPRESSION_RATE_LIMIT = 60        # 60 ops/minute
```

### Priority Levels

```python
from cohezion.security.compression_utils import CompressionPriority

# Available priorities
CompressionPriority.CRITICAL  # Bypasses rate limit
CompressionPriority.HIGH  # Normal rate limit
CompressionPriority.NORMAL  # Normal rate limit
CompressionPriority.LOW  # Normal rate limit
```

## Operational Guidelines

### Monitoring

Watch for these security events:
```bash
# Check for compression bombs
grep "compression_bomb_detected" /var/log/cohezion/app.log

# Check for suspicious ratios
grep "suspicious_compression_ratio" /var/log/cohezion/app.log

# Check rate limit violations
grep "compression_rate_limited" /var/log/cohezion/app.log
```

### Alerting Thresholds

| Condition | Action |
|-----------|--------|
| Single bomb detected | Log error, block operation |
| 3+ suspicious attempts from same source | Log critical, alert security team |
| Rate limit exceeded 10+ times in 1 hour | Review for DoS attack |
| Any decompression exceeding 1GB | Log error, investigate source |

### Incident Response

1. **Detect Bomb**
   - Security event logged
   - Operation blocked
   - File cleaned up automatically

2. **Investigate**
   - Check source of data
   - Review recent operations
   - Identify attack vector

3. **Respond**
   - Block suspicious sources
   - Rotate affected keys/tokens
   - Document in security log

## Compliance

This fix addresses:
- ✅ PRD Section 5.3 (Resource Protection)
- ✅ Epic SEC-003 (Security Hardening)
- ✅ Story SEC-009 (Compression Bomb Protection)

### Security Standards

- OWASP Top 10: A05 (Security Misconfiguration)
- CWE-409: Improper Handling of Highly Compressed Data (Data Amplification)
- CWE-400: Uncontrolled Resource Consumption

## References

### Documentation
- [PRD Section 5.3](../prd/resource_protection.md)
- [Security Architecture](ARCHITECTURE.md#security)
- [API Security Guide](API_SECURITY.md)

### Related Modules
- `src/cohezion/security/compression_utils.py`
- `src/cohezion/compound/metrics_persistence.py`
- `tests/security/test_compression_bomb.py`

### External References
- [ZIP Bomb Wikipedia](https://en.wikipedia.org/wiki/Zip_bomb)
- [OWASP Compression Bombs](https://owasp.org/www-community/attacks/Compression_Bombs)

## Validation

### Acceptance Criteria

- [x] Compression ratio limits enforced (100:1 max)
- [x] Compressed size limits active (100MB max)
- [x] Decompressed size limits active (1GB max)
- [x] Stream-based processing implemented
- [x] Bomb detection implemented
- [x] Rate limiting active (60 ops/min)
- [x] Security event logging active
- [x] Integration tests pass
- [x] Documentation complete

### Verification Commands

```bash
# Run security tests
make test-security

# Run type checking
make type-check

# Run linting
make lint

# Verify implementation
python -c "from cohezion.security.compression_utils import *; print('✅ Security module loaded')"
```

## Contact

- **Security Team:** security@cohezion.ai
- **Emergency:** security-critical@cohezion.ai
- **Documentation:** docs@cohezion.ai

---

**Last Updated:** March 1, 2026  
**Next Review:** March 1, 2027  
**Owner:** Security Team
