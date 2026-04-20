
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("CohezionComponentMCP")

# Component Library (Mocked as strings for this implementation)
COMPONENTS = {
    "MissionHUD": {
        "props": ["stability", "r_zero", "eco_metrics"],
        "jsx": """
const MissionHUD = ({ stability, r_zero, eco_metrics }) => (
  <div className="hud-panel glass">
    <h2>Mission Control</h2>
    <div className="metric">Stability: <span className="value">{stability.toFixed(2)}</span></div>
    <div className="metric">R-Zero: <span className="value">{r_zero.toFixed(2)}</span></div>
    <div className="metric">Habitat Quality: <span className="value">{eco_metrics.habitat_quality.toFixed(2)}</span></div>
  </div>
);
export default MissionHUD;
""",
    },
    "ManifoldNode": {
        "props": ["position", "color", "intensity"],
        "jsx": """
import { Sphere } from '@react-three/drei';

const ManifoldNode = ({ position, color, intensity }) => (
  <Sphere position={position} args={[0.05, 16, 16]}>
    <meshStandardMaterial color={color} emissive={color} emissiveIntensity={intensity} />
  </Sphere>
);
export default ManifoldNode;
""",
    },
}


@mcp.tool()
def get_component_vetted_code(name: str) -> str:
    """Returns the vetted JSX/TSX code for a specific high-fidelity component."""
    comp = COMPONENTS.get(name)
    if not comp:
        return f"Error: Component '{name}' not found in vetted registry."
    return comp["jsx"]


@mcp.tool()
def list_vetted_components() -> list[str]:
    """Lists all pre-vetted components available for the Glass Lattice UI."""
    return list(COMPONENTS.keys())


if __name__ == "__main__":
    mcp.run()
