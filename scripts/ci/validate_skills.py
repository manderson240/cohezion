#!/usr/bin/env python3
"""CI: Validate PRIME skill definitions parse correctly and generate valid code."""

from __future__ import annotations

import sys

from cohezion.core.template_engine import SkillSpec, TemplateEngine


def main() -> int:
    """Parse all skills, compile generated stubs and configs."""
    engine = TemplateEngine()
    specs: list[SkillSpec] = engine.parse_all()

    if len(specs) < 100:
        print(f"FAIL: Only {len(specs)} skills parsed (expected >= 100)")
        return 1

    stub_ok = 0
    stub_fail = 0
    config_ok = 0
    config_fail = 0

    for spec in specs:
        # Validate agent stub compiles
        stub_src = engine.generate_agent_stub(spec)
        try:
            compile(stub_src, f"<stub:{spec.name}>", "exec")
            stub_ok += 1
        except SyntaxError as exc:
            print(f"FAIL: Stub syntax error for {spec.name}: {exc}")
            stub_fail += 1

        # Validate config class compiles
        config_src = engine.generate_config_class(spec)
        try:
            compile(config_src, f"<config:{spec.name}>", "exec")
            config_ok += 1
        except SyntaxError as exc:
            print(f"FAIL: Config syntax error for {spec.name}: {exc}")
            config_fail += 1

    print(f"Skills parsed:     {len(specs)}")
    print(f"Stubs compiled:    {stub_ok} OK, {stub_fail} failed")
    print(f"Configs compiled:  {config_ok} OK, {config_fail} failed")

    if stub_fail > 0 or config_fail > 0:
        print("FAIL: Some generated code has syntax errors")
        return 1

    print("OK: All skills parsed and generated code compiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
