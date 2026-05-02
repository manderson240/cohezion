#!/usr/bin/env python3
import sys

from cohezion.governance.guardian import GuardianRegistry, get_guardian_cli


def main():
    args = get_guardian_cli()
    registry = GuardianRegistry()

    # Dynamically register all guards
    registry.discover_and_register_all()

    # Run logic
    if args.all:
        success = registry.run_all(auto_heal=args.heal)
    elif args.guard:
        # Find specific guard
        target = next((g for g in registry.guards if g.name == args.guard), None)
        if target:
            success = target.run(auto_heal=args.heal)
            target.report()
        else:
            print(f"Error: Guard '{args.guard}' not found.")
            sys.exit(1)
    else:
        # Default to running all without heal if no args
        success = registry.run_all(auto_heal=args.heal)

    if not success:
        if args.heal:
            # Collect all violations for the journey intent
            all_violations = []
            for guard in registry.guards:
                all_violations.extend(guard.violations)

            print("\n[!] Auto-healing failed to resolve all violations.")
            print("[!] Triggering Ouroboros self-healing loop...")
            import subprocess

            try:
                # Trigger Agentic Repair via Journey
                subprocess.run(
                    [
                        "uv",
                        "run",
                        "python",
                        "-m",
                        "cohezion",
                        "journey",
                        "start",
                        "Resolve guardian invariant violations: " + ", ".join(all_violations),
                    ],
                    check=False,
                )
            except Exception as e:
                print(f"Error triggering Ouroboros: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
