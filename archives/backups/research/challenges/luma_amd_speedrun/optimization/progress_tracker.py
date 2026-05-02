#!/usr/bin/env python3
"""
PROGRESS TRACKER FOR UNSTOPPABLE OPTIMIZATION
Simple utility to track and visualize optimization progress
"""

import glob
import json
from datetime import datetime
from pathlib import Path


def find_latest_session():
    """Find the most recent optimization session"""
    sessions = glob.glob("/tmp/opt_session_*")
    if not sessions:
        return None
    return max(sessions, key=lambda x: int(x.split("_")[-1]) if x.split("_")[-1].isdigit() else 0)


def load_session_data(session_dir):
    """Load data from an optimization session"""
    session_path = Path(session_dir)

    # Load performance data
    performance_file = session_path / "performance.jsonl"
    performance_data = []
    if performance_file.exists():
        with open(performance_file) as f:
            for line in f:
                if line.strip():
                    try:
                        performance_data.append(json.loads(line))
                    except:
                        pass

    # Load lessons learned
    lessons_file = session_path / "lessons learned.jsonl"
    lessons_data = []
    if lessons_file.exists():
        with open(lessons_file) as f:
            for line in f:
                if line.strip():
                    try:
                        lessons_data.append(json.loads(line))
                    except:
                        pass

    return {"performance": performance_data, "lessons": lessons_data, "session_dir": session_dir}


def analyze_progress(session_data):
    """Analyze and display optimization progress"""
    perf_data = session_data["performance"]
    lessons_data = session_data["lessons"]

    if not perf_data:
        print("📊 No performance data yet - optimization may just be starting")
        return

    print("📈 OPTIMIZATION PROGRESS ANALYSIS")
    print(f"Session: {session_data['session_dir']}")
    print(
        f"Total Records: {len(perf_data)} performance entries, {len(lessons_data)} lesson entries"
    )
    print("-" * 50)

    # Group by kernel
    kernel_data = {}
    for entry in perf_data:
        kernel = entry.get("kernel", "unknown")
        if kernel not in kernel_data:
            kernel_data[kernel] = []
        kernel_data[kernel].append(entry)

    # Analyze each kernel
    for kernel, entries in kernel_data.items():
        print(f"\n🎯 {kernel.upper()}")
        successful = [e for e in entries if e.get("status") == "success"]
        failed = [e for e in entries if e.get("status") != "success"]

        print(f"   Total attempts: {len(entries)}")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed/Skipped: {len(failed)}")

        if successful:
            # Find best performance
            best_entry = min(
                successful,
                key=lambda x: x.get("performance_after", {}).get("execution_time_ms", float("inf")),
            )
            best_time = best_entry.get("performance_after", {}).get("execution_time_ms", "N/A")
            baseline_time = best_entry.get("performance_before", {}).get("execution_time_ms", "N/A")

            if isinstance(best_time, (int, float)) and isinstance(baseline_time, (int, float)):
                improvement = ((baseline_time - best_time) / baseline_time) * 100
                print(f"   Best time: {best_time:.3f}ms (baseline: {baseline_time:.3f}ms)")
                print(f"   Improvement: {improvement:+.1f}%")
            else:
                print(f"   Best time: {best_time}ms")
                print(f"   Baseline: {baseline_time}ms")

        # Show recent attempts
        recent = entries[-3:] if len(entries) >= 3 else entries
        print("   Recent attempts:")
        for entry in reversed(recent):
            status = entry.get("status", "unknown")
            hypothesis = entry.get("hypothesis", "No hypothesis")[:50] + "..."
            timestamp = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%H:%M:%S")
            print(f"     [{timestamp}] {status}: {hypothesis}")

    # Show key lessons learned
    if lessons_data:
        print("\n💡 KEY LESSONS LEARNED (Most Recent):")
        recent_lessons = lessons_data[-5:] if len(lessons_data) >= 5 else lessons_data
        for i, lesson_entry in enumerate(reversed(recent_lessons), 1):
            timestamp = datetime.fromtimestamp(lesson_entry.get("timestamp", 0)).strftime(
                "%m/%d %H:%M"
            )
            lessons = lesson_entry.get("lessons", [])
            if lessons:
                print(f"   {i}. [{timestamp}] {lessons[0]}")

    # Calculate overall metrics
    total_attempts = len(perf_data)
    total_success = len([e for e in perf_data if e.get("status") == "success"])
    success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0

    print("\n📊 OVERALL METRICS:")
    print(f"   Success Rate: {success_rate:.1f}% ({total_success}/{total_attempts})")
    print("   Persistence Score: HIGH (system continues despite setbacks)")

    # Show session directory
    print("\n📁 Session Data:")
    print(f"   Location: {session_data['session_dir']}")
    print(
        f"   Files: {len(list(Path(session_data['session_dir']).iterdir()))} files in session directory"
    )


def main():
    print("📈 UNSTOPPABLE OPTIMIZATION PROGRESS TRACKER")
    print("=" * 50)

    latest_session = find_latest_session()
    if not latest_session:
        print("🔍 No optimization sessions found yet.")
        print("💡 Run the unstoppable optimizer first to generate data.")
        print("🚀 Try: python3 /tmp/quick_start_unstoppable.py")
        return

    print(f"🎯 Found latest session: {latest_session}")
    session_data = load_session_data(latest_session)
    analyze_progress(session_data)

    print("\n" + "=" * 50)
    print("💡 TIP: Run this tracker periodically to see your progress!")
    print("🔥 Remember: Every data point, success or failure, moves you forward!")


if __name__ == "__main__":
    main()
