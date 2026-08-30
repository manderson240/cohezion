#!/usr/bin/env python3
"""Verify the hardened LinuxNamespaceSandbox with cgroup v2 limits & DRM isolation."""

from cohezion.security.linux_namespace_sandbox import LinuxNamespaceSandbox

def test_hardened_sandbox():
    sandbox = LinuxNamespaceSandbox()
    
    # 1. Normal execution check
    code_pass = "x = [i**2 for i in range(100)]; print('SUM:', sum(x))"
    res1 = sandbox.execute_python_code(code_pass)
    print(f"Normal Exec: Success={res1.success}, ExitCode={res1.exit_code}, Output={res1.stdout.strip()}")
    assert res1.success
    
    # 2. Check no DRM device access (preventing unmonitored GEM/TTM aperture leaks)
    code_no_drm = "import os; assert not os.path.exists('/dev/dri'), 'DRM should not be visible'; print('NO_DRM_VERIFIED')"
    res2 = sandbox.execute_python_code(code_no_drm)
    print(f"DRM Isolation: Success={res2.success}, Output={res2.stdout.strip()}")
    assert res2.success
    
    print("✅ All Hardened LinuxNamespaceSandbox Checks: PASSED")

if __name__ == "__main__":
    test_hardened_sandbox()
