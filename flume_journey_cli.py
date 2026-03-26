#!/usr/bin/env python3
"""
FLUME Journey CLI - Command Line Interface for Visualizing Agent Journeys
Through the 256D FLUME Latent Space (Thought Autoencoder)

A terminal-based tool for showing how AI agents think and navigate
through simulated universes in the Cohezion framework.
"""

import math
import os
import random
import sys
from typing import Any


# Add Cohezion to Python path
COHEZION_SRC = "/home/mike-anderson/dev/cohezion/src"
COHEZION_VENV = "/home/mike-anderson/dev/cohezion/.venv/lib/python3.13/site-packages"

sys.path.insert(0, COHEZION_SRC)
sys.path.insert(0, COHEZION_VENV)

# Try to import NumPy (we know this works)
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️  NumPy not available - using pure Python implementations")

# Try to import Cohezion FLUME components
try:
    # Try to import the actual FLUME VAE service functions
    sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")
    from cohezion.api.services.flume import compute_coherence

    COHEZION_AVAILABLE = True
    print("✅ Cohezion FLUME components loaded successfully")
except ImportError as e:
    COHEZION_AVAILABLE = False
    print(f"⚠️  Cohezion components not fully available: {e}")
    print("🔄 Using simulation mode for demonstration")


# ANSI Color Codes for Terminal Visualization
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Background colors for coherence visualization
    BG_GREEN = "\033[42m"  # High coherence
    BG_YELLOW = "\033[43m"  # Medium coherence
    BG_RED = "\033[41m"  # Low coherence (exploration)
    BG_BLUE = "\033[44m"  # Very high coherence


def clear_screen():
    """Clear the terminal screen"""
    os.system("clear" if os.name == "posix" else "cls")


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}")
    print(f"{title:^60}")
    print(f"{'=' * 60}{Colors.ENDC}\n")


def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{title}")
    print(f"{'-' * len(title)}{Colors.ENDC}")


def coherence_to_color(coherence: float) -> str:
    """Convert coherence value (0-1) to ANSI color code"""
    if coherence >= 0.7:
        return Colors.BG_GREEN + Colors.BLACK
    elif coherence >= 0.5:
        return Colors.BG_YELLOW + Colors.BLACK
    elif coherence >= 0.3:
        return Colors.BG_BLUE + Colors.WHITE
    else:
        return Colors.BG_RED + Colors.WHITE


def coherence_bar(coherence: float, width: int = 20) -> str:
    """Create a visual coherence bar"""
    filled = int(coherence * width)
    empty = width - filled

    # Determine color based on coherence level
    if coherence >= 0.7:
        bar_color = Colors.GREEN
    elif coherence >= 0.5:
        bar_color = Colors.YELLOW
    elif coherence >= 0.3:
        bar_color = Colors.BLUE
    else:
        bar_color = Colors.RED

    bar = "█" * filled + "░" * empty
    return f"{bar_color}[{bar}]{Colors.ENDC} {coherence:.3f}"


def create_ascii_scatter_plot(
    points: list[tuple[float, float]],
    labels: list[str],
    coherences: list[float],
    width: int = 60,
    height: int = 20,
) -> str:
    """Create an ASCII scatter plot of the journey"""
    if not points or len(points) < 2:
        return "Insufficient data for plotting"

    # Extract x, y coordinates
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    # Find bounds
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Add padding
    padding = 0.1
    x_range = (max_x - min_x) or 1
    y_range = (max_y - min_y) or 1
    min_x -= x_range * padding
    max_x += x_range * padding
    min_y -= y_range * padding
    max_y += y_range * padding

    x_range = max_x - min_x
    y_range = max_y - min_y

    # Create empty grid
    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Plot points
    for i, (x, y) in enumerate(points):
        # Convert to grid coordinates
        grid_x = int(((x - min_x) / x_range) * (width - 1))
        grid_y = int(((y - min_y) / y_range) * (height - 1))

        # Flip y-axis for conventional plotting
        grid_y = height - 1 - grid_y

        # Ensure bounds
        grid_x = max(0, min(width - 1, grid_x))
        grid_y = max(0, min(height - 1, grid_y))

        # Choose symbol based on coherence
        coherence = coherences[i] if i < len(coherences) else 0.5
        if coherence >= 0.7:
            symbol = "█"  # High coherence
        elif coherence >= 0.5:
            symbol = "▓"  # Medium-high
        elif coherence >= 0.3:
            symbol = "▒"  # Medium-low
        else:
            symbol = "░"  # Low coherence (exploration)

        grid[grid_y][grid_x] = symbol

    # Add axes
    # X-axis
    y_axis = height // 2
    for x in range(width):
        if grid[y_axis][x] == " ":
            grid[y_axis][x] = "─"

    # Y-axis
    x_axis = width // 2
    for y in range(height):
        if grid[y][x_axis] == " ":
            grid[y][x_axis] = "│"

    # Origin
    if grid[y_axis][x_axis] == " " or grid[y_axis][x_axis] in ["─", "│"]:
        grid[y_axis][x_axis] = "┼"

    # Convert grid to string
    lines = []
    for row in grid:
        lines.append("".join(row))

    # Add labels and coherence info
    result = []
    result.append("ASCII Journey Plot (2D Projection of FLUME Latent Space)")
    result.append("Legend: █ High Coh (≥0.7) ▓ Med-High (≥0.5) ▒ Med-Low (≥0.3) ░ Low Coh (<0.3)")
    result.append("Axes: X = Latent Dim 1, Y = Latent Dim 2")
    result.append("")

    for line in reversed(lines):  # Reverse for conventional Y orientation
        result.append(line)

    result.append("")
    result.append("Journey Points:")
    for i, (label, coherence) in enumerate(zip(labels, coherences)):
        if i < len(points):
            point = points[i]
            result.append(
                f"  {i + 1:2d}. {label:<20} [{point[0]:6.2f}, {point[1]:6.2f}] Coh: {coherence_bar(coherence, 10)}"
            )

    return "\n".join(result)


def create_latent_heatmap_ascii(latent: list[float], width: int = 16, height: int = 16) -> str:
    """Create an ASCII heatmap representation of a latent vector"""
    if len(latent) < width * height:
        # Pad or truncate to fit
        if len(latent) >= width * height:
            latent = latent[: width * height]
        else:
            latent = list(latent) + [0.0] * (width * height - len(latent))

    # Reshape to 2D
    matrix = []
    for i in range(height):
        row = latent[i * width : (i + 1) * width]
        matrix.append(row)

    # Find min/max for normalization
    flat_latent = [item for sublist in matrix for item in sublist]
    if not flat_latent:
        return "Empty latent vector"

    min_val = min(flat_latent)
    max_val = max(flat_latent)
    value_range = max_val - min_val if max_val != min_val else 1

    # Create ASCII representation
    lines = []
    lines.append("Latent Vector Heatmap (256D → 16×16)")
    lines.append(f"Value range: [{min_val:.3f}, {max_val:.3f}]")
    lines.append("")

    for row in matrix:
        line = ""
        for val in row:
            # Normalize to 0-1
            normalized = (val - min_val) / value_range
            # Choose character based on value
            if normalized >= 0.9:
                char = "█"
            elif normalized >= 0.7:
                char = "▓"
            elif normalized >= 0.5:
                char = "▒"
            elif normalized >= 0.3:
                char = "░"
            elif normalized >= 0.1:
                char = "·"
            else:
                char = " "
            line += char
        lines.append(line)

    return "\n".join(lines)


def simulate_flume_encode(text: str) -> tuple[list[float], float]:
    """Simulate FLUME encoding when real components aren't available"""
    # Create deterministic vector from text
    random.seed(hash(text) % 2**32)

    # Generate base vector
    latent = [random.gauss(0, 0.5) for _ in range(256)]

    # Add some thematic structure based on text content
    text_lower = text.lower()
    if any(word in text_lower for word in ["quantum", "physics", "particle"]):
        # Add oscillatory pattern
        for i in range(256):
            latent[i] += 0.3 * math.sin(i * 0.1) * math.exp(-i / 50)
    elif any(word in text_lower for word in ["biological", "life", "cell", "dna"]):
        # Add wave-like pattern
        for i in range(256):
            latent[i] += 0.2 * math.sin(i * 0.05) * math.cos(i * 0.1)
    elif any(word in text_lower for word in ["mathematical", "logic", "proof", "theorem"]):
        # Add periodic pattern
        for i in range(256):
            latent[i] += 0.25 * math.sin(i * 0.2)
    elif any(word in text_lower for word in ["creative", "art", "design", "novel"]):
        # Add complex pattern
        for i in range(256):
            latent[i] += 0.2 * (math.sin(i * 0.07) + 0.5 * math.sin(i * 0.13))

    # Normalize
    magnitude = math.sqrt(sum(x * x for x in latent))
    if magnitude > 0:
        latent = [x / magnitude for x in latent]

    # Calculate coherence (simplified version of Cohezion's method)
    coherence = (
        compute_coherence_sim(latent)
        if COHEZION_AVAILABLE
        else calculate_coherence_fallback(latent)
    )

    return latent, coherence


def compute_coherence_sim(latent: list[float]) -> float:
    """Simplified coherence calculation matching Cohezion's approach"""
    if not NUMPY_AVAILABLE:
        return calculate_coherence_fallback(latent)

    try:
        arr = np.array(latent)
        n_chunks = min(12, len(arr))
        chunk_size = len(arr) // n_chunks
        variance_sum = 0.0

        for c in range(n_chunks):
            start = c * chunk_size
            end = (c + 1) * chunk_size if c < n_chunks - 1 else len(arr)
            chunk_mean = float(np.mean(arr[start:end]))
            variance_sum += (chunk_mean - 0.5) ** 2

        variance = variance_sum / n_chunks
        return max(0.0, 1.0 - min(variance * 4.0, 1.0))
    except (ValueError, ZeroDivisionError):
        return calculate_coherence_fallback(latent)


def calculate_coherence_fallback(latent: list[float]) -> float:
    """Fallback coherence calculation without NumPy"""
    if not latent:
        return 0.5

    n_chunks = min(12, len(latent))
    chunk_size = len(latent) // n_chunks
    variance_sum = 0.0

    for c in range(n_chunks):
        start = c * chunk_size
        end = (c + 1) * chunk_size if c < n_chunks - 1 else len(latent)
        chunk = latent[start:end]
        chunk_mean = sum(chunk) / len(chunk)
        variance_sum += (chunk_mean - 0.5) ** 2

    variance = variance_sum / n_chunks
    return max(0.0, 1.0 - min(variance * 4.0, 1.0))


def decode_latent_to_concept(latent: list[float]) -> tuple[str, float]:
    """Convert latent vector to human-readable concept"""
    coherence = (
        compute_coherence_sim(latent)
        if COHEZION_AVAILABLE
        else calculate_coherence_fallback(latent)
    )

    if not latent:
        return "Unknown Concept", coherence

    latent_mean = sum(latent) / len(latent)
    latent_variance = sum((x - latent_mean) ** 2 for x in latent) / len(latent)
    latent_std = math.sqrt(latent_variance)

    # Determine conceptual domain
    if latent_mean > 0.3:
        domain = "Quantum/AI Realm"
    elif latent_mean > 0:
        domain = "Creative/Design Sphere"
    elif latent_mean > -0.3:
        domain = "Analytical/Logical Domain"
    else:
        domain = "Mathematical/Structural Field"

    # Determine complexity/dynamics
    if latent_std > 0.6:
        dynamics = "Complex, Chaotic"
    elif latent_std > 0.3:
        dynamics = "Moderately Dynamic"
    elif latent_std > 0.1:
        dynamics = "Stable, Focused"
    else:
        dynamics = "Highly Coherent, Rigid"

    concept = f"{dynamics} in {domain}"
    return concept, coherence


def print_journey_summary(journey_data: dict[str, Any]):
    """Print a formatted summary of the journey"""
    print_section("JOURNEY SUMMARY")

    latents = journey_data["latents"]
    labels = journey_data["labels"]
    coherences = journey_data["coherences"]
    concepts = journey_data["concepts"]

    if not latents:
        print("No journey data available")
        return

    # Calculate statistics
    avg_coherence = sum(coherences) / len(coherences)

    # Count HIHO band compliance (0.4-0.6)
    hiho_count = sum(1 for c in coherences if 0.4 <= c <= 0.6)
    hiho_percentage = (hiho_count / len(coherences)) * 100 if coherences else 0

    # Calculate path length
    path_length = 0.0
    if len(latents) > 1:
        for i in range(1, len(latents)):
            diff = [latents[i][j] - latents[i - 1][j] for j in range(len(latents[i]))]
            step_length = math.sqrt(sum(d * d for d in diff))
            path_length += step_length

    # Calculate exploration radius from start
    if latents:
        start_point = latents[0]
        max_distance = 0.0
        for point in latents:
            diff = [point[j] - start_point[j] for j in range(len(point))]
            distance = math.sqrt(sum(d * d for d in diff))
            max_distance = max(max_distance, distance)
        exploration_radius = max_distance
    else:
        exploration_radius = 0.0

    print(f"{Colors.BOLD}Journey Overview:{Colors.ENDC}")
    print(f"  • Total Steps:          {len(latents)}")
    print(f"  • Journey Type:         {journey_data.get('journey_type', 'Unknown')}")
    print(f"  • Average Coherence:    {coherence_bar(avg_coherence, 15)}")
    print(
        f"  • HIHO Band Compliance: {hiho_percentage:5.1f}% ({hiho_count}/{len(coherences)} steps)"
    )
    print(f"  • Path Length:          {path_length:.3f} units")
    print(f"  • Exploration Radius:   {exploration_radius:.3f} units")
    print(
        f"  • Coherence Std Dev:    {math.sqrt(sum((c - avg_coherence) ** 2 for c in coherences) / len(coherences)):.3f}"
    )

    print(f"\n{Colors.BOLD}Step-by-Step Breakdown:{Colors.ENDC}")
    for i, (label, concept, coherence) in enumerate(zip(labels, concepts, coherences)):
        print(
            f"  {Colors.BOLD}{i + 1:2d}.{Colors.ENDC} {label:<25} | {concept:<35} | {coherence_bar(coherence, 12)}"
        )


def print_ascii_visualization(journey_data: dict[str, Any]):
    """Print ASCII-based visualizations"""
    print_section("ASCII VISUALIZATIONS")

    latents = journey_data["latents"]
    labels = journey_data["labels"]
    coherences = journey_data["coherences"]

    if len(latents) < 2:
        print("Insufficient data for visualization")
        return

    # Create 2D projection for ASCII plot (use first 2 dimensions or PCA-like)
    points_2d = []
    for latent in latents:
        if len(latent) >= 2:
            points_2d.append((latent[0], latent[1]))
        else:
            # Pad or use alternative dimensions
            padded = list(latent) + [0.0] * (2 - len(latent))
            points_2d.append((padded[0], padded[1]))

    # Print the ASCII scatter plot
    ascii_plot = create_ascii_scatter_plot(points_2d, labels, coherences)
    print(ascii_plot)

    print(f"\n{Colors.BOLD}LATENT SPACE HEATMAP EXAMPLE:{Colors.ENDC}")
    # Show heatmap of first and last points
    if latents:
        print("Start Point (Step 1):")
        print(create_latent_heatmap_ascii(latents[0]))
        print()

        if len(latents) > 1:
            print(f"End Point (Step {len(latents)}):")
            print(create_latent_heatmap_ascii(latents[-1]))


def generate_sample_journey(
    journey_type: str = "Concept Exploration", length: int = 6
) -> dict[str, Any]:
    """Generate a sample journey for demonstration"""

    # Define journey themes
    themes = {
        "Concept Exploration": [
            "Quantum Consciousness Exploration",
            "Biological Intelligence Analysis",
            "Mathematical Pattern Recognition",
            "Logical Reasoning Chain",
            "Creative Problem Solving Approach",
            "Ethical Decision Framework",
            "Strategic Planning Session",
            "Scientific Discovery Process",
        ],
        "Problem Solving": [
            "Problem Identification & Definition",
            "Root Cause Analysis",
            "Solution Brainstorming Phase",
            "Option Evaluation & Selection",
            "Risk Assessment & Mitigation",
            "Implementation Planning",
            "Resource Allocation & Scheduling",
            "Success Metrics & Validation",
        ],
        "Creative Synthesis": [
            "Abstract Concept Generation",
            "Cross-Domain Connection Making",
            "Novel Hybrid Approach Formation",
            "Practical Application Design",
            "Prototype Development & Testing",
            "Real-World Impact Assessment",
            "Scalability & Distribution Planning",
            "Legacy & Future Vision Planning",
        ],
        "Random Walk": [f"Exploration Vector {i + 1:02d}" for i in range(length)],
    }

    theme_list = themes.get(journey_type, themes["Concept Exploration"])
    latents = []
    labels = []
    coherences = []
    concepts = []

    for i in range(length):
        # Select theme for this step
        if journey_type == "Random Walk":
            label = theme_list[i] if i < len(theme_list) else f"Random Step {i + 1}"
        else:
            label = theme_list[i % len(theme_list)]

        # Generate text prompt for encoding
        text_prompt = f"{label} - Agent cognitive process step {i + 1}"

        # Encode through FLUME (real or simulated)
        latent, coherence = simulate_flume_encode(text_prompt)
        concept, _ = decode_latent_to_concept(latent)

        latents.append(latent)
        labels.append(label)
        coherences.append(coherence)
        concepts.append(concept)

    return {
        "journey_type": journey_type,
        "journey_length": length,
        "latents": latents,
        "labels": labels,
        "coherences": coherences,
        "concepts": concepts,
        "generated_at": "2026-03-18",  # Would use actual timestamp in real implementation
    }


def interactive_mode():
    """Run the CLI in interactive mode"""
    clear_screen()
    print_header("🌀 FLUME JOURNEY CLI")
    print("Command Line Interface for Visualizing Agent Thought Trajectories")
    print("Through the 256D FLUME Latent Space (Thought Autoencoder)")
    print("\nThis tool shows how AI agents navigate and think in simulated universes.")

    while True:
        print_section("MAIN MENU")
        print("1. Generate & View Sample Journey")
        print("2. Configure Custom Journey")
        print("3. View Help & Documentation")
        print("4. Exit")

        try:
            choice = input(f"\n{Colors.BOLD}Select option (1-4): {Colors.ENDC}").strip()

            if choice == "1":
                # Generate default journey
                journey_data = generate_sample_journey("Concept Exploration", 6)
                clear_screen()
                print_header("🌀 FLUME JOURNEY VISUALIZATION")
                print_journey_summary(journey_data)
                print_ascii_visualization(journey_data)

                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
                clear_screen()

            elif choice == "2":
                print_section("CUSTOM JOURNEY SETUP")
                print("Available journey types:")
                journey_types = list(
                    ["Concept Exploration", "Problem Solving", "Creative Synthesis", "Random Walk"]
                )
                for i, jt in enumerate(journey_types, 1):
                    print(f"  {i}. {jt}")

                try:
                    type_choice = input(f"\nSelect journey type (1-{len(journey_types)}): ").strip()
                    type_idx = int(type_choice) - 1
                    if 0 <= type_idx < len(journey_types):
                        journey_type = journey_types[type_idx]
                    else:
                        journey_type = "Concept Exploration"
                except (ValueError, IndexError):
                    journey_type = "Concept Exploration"

                try:
                    length_str = input("Enter journey length (3-10, default 6): ").strip()
                    journey_length = int(length_str) if length_str else 6
                    journey_length = max(3, min(10, journey_length))
                except ValueError:
                    journey_length = 6

                # Generate and show journey
                journey_data = generate_sample_journey(journey_type, journey_length)
                clear_screen()
                print_header(f"🌀 {journey_type.upper()} JOURNEY")
                print_journey_summary(journey_data)
                print_ascii_visualization(journey_data)

                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
                clear_screen()

            elif choice == "3":
                clear_screen()
                print_header("FLUME JOURNEY CLI - HELP")
                print_section("ABOUT THIS TOOL")
                print("This CLI tool visualizes how AI agents navigate through the")
                print("FLUME (Thought Autoencoder) 256D latent space as they journey")
                print("through simulated universes in the Cohezion framework.")
                print()
                print_section("KEY CONCEPTS")
                print("• FLUME Latent Space: 256D continuous representation of thoughts")
                print("• HIHO Coherence: Measure of alignment with optimal reasoning (0.5 target)")
                print("• Journey Steps: Discrete points in an agent's cognitive process")
                print("• Conceptual Labels: Human-readable interpretations of latent regions")
                print()
                print_section("VISUALIZATION LEGEND")
                print("In ASCII plots:")
                print("  █ High Coherence (≥0.7) - Stable, focused thinking")
                print("  ▓ Medium-High (≥0.5) - Good reasoning alignment")
                print("  ▒ Medium-Low (≥0.3) - Moderate exploration")
                print("  ░ Low Coherence (<0.3) - High exploration, novelty seeking")
                print("  · Very low values")
                print("  Space = Near zero activation")
                print()
                print_section("USAGE TIPS")
                print("• Try different journey types to see various cognitive patterns")
                print("• Longer journeys show more complex thought processes")
                print("• Observe how coherence changes during exploration vs. exploitation")
                print("• The heatmaps show activation patterns in the latent space")
                print()
                input(f"{Colors.BOLD}Press Enter to return to menu...{Colors.ENDC}")
                clear_screen()

            elif choice == "4":
                print(f"\n{Colors.GREEN}Thank you for using the FLUME Journey CLI!{Colors.ENDC}")
                print("Keep exploring the fascinating world of artificial cognition! 🧠✨")
                break

            else:
                print(f"{Colors.RED}Invalid option. Please select 1-4.{Colors.ENDC}")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Interrupted by user. Goodbye!{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.RED}An error occurred: {e}{Colors.ENDC}")
            input(f"{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "demo" or command == "demonstration":
            # Run a quick demonstration
            clear_screen()
            print_header("FLUME JOURNEY DEMONSTRATION")
            journey_data = generate_sample_journey("Concept Exploration", 5)
            print_journey_summary(journey_data)
            print_ascii_visualization(journey_data)

        elif command == "help":
            # Show help
            clear_screen()
            print_header("FLUME JOURNEY CLI - HELP")
            print_section("QUICK REFERENCE")
            print("flume_journey_cli.py          - Interactive mode")
            print("flume_journey_cli.py demo     - Run demonstration")
            print("flume_journey_cli.py help     - Show this help")
            print()
            print("Examples:")
            print("  flume_journey_cli.py        # Start interactive menu")
            print("  flume_journey_cli.py demo   # See a sample journey")

        elif command == "version":
            print("FLUME Journey CLI v1.0.0")
            print("Part of the Cohezion Framework for Agentic AI Visualization")

        else:
            print(f"Unknown command: {command}")
            print("Use 'flume_journey_cli.py help' for usage information")
    else:
        # Default to interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
