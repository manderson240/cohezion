"""BMAD CIS (Creative Intelligence Studio) tool routes."""

from aiohttp import web

from ._shared import routes


@routes.post("/tools/bmad_cis_brainstorming")
async def tool_bmad_cis_brainstorming(request: web.Request) -> web.Response:
    """Brainstorming tool."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_cis_brainstorming",
                "topic": data.get("topic"),
                "participants": data.get("participants", 1),
                "timebox_minutes": data.get("timebox_minutes", 15),
                "message": "Brainstorming session guide provided",
                "techniques": [
                    "Mind Mapping",
                    "Rapid Ideation (5 min)",
                    "Yes, And...",
                    "Crazy 8s",
                    "SCAMPER",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_cis_design_thinking")
async def tool_bmad_cis_design_thinking(request: web.Request) -> web.Response:
    """Apply design thinking methodology."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_cis_design_thinking",
                "problem": data.get("problem", ""),
                "phases": [
                    {"phase": "Empathize", "activity": "User research and interviews"},
                    {"phase": "Define", "activity": "Synthesize findings into problem statement"},
                    {"phase": "Ideate", "activity": "Generate wide range of solutions"},
                    {"phase": "Prototype", "activity": "Build low-fidelity prototypes"},
                    {"phase": "Test", "activity": "Validate with real users"},
                ],
                "deliverables": ["Personas", "Journey maps", "Prototypes", "Test results"],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_cis_six_thinking_hats")
async def tool_bmad_cis_six_thinking_hats(request: web.Request) -> web.Response:
    """Apply Six Thinking Hats technique."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_cis_six_thinking_hats",
                "topic": data.get("topic", ""),
                "hats": [
                    {
                        "color": "White",
                        "focus": "Facts and information",
                        "questions": ["What do we know?", "What data do we have?"],
                    },
                    {
                        "color": "Red",
                        "focus": "Emotions and feelings",
                        "questions": ["How do we feel?", "What is our gut reaction?"],
                    },
                    {
                        "color": "Black",
                        "focus": "Critical judgment",
                        "questions": ["What could go wrong?", "What are the risks?"],
                    },
                    {
                        "color": "Yellow",
                        "focus": "Optimism",
                        "questions": ["What are the benefits?", "Why will this work?"],
                    },
                    {
                        "color": "Green",
                        "focus": "Creativity",
                        "questions": ["What new ideas?", "What alternatives?"],
                    },
                    {
                        "color": "Blue",
                        "focus": "Process control",
                        "questions": ["What is next?", "How to organize?"],
                    },
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_cis_scamper")
async def tool_bmad_cis_scamper(request: web.Request) -> web.Response:
    """Apply SCAMPER creativity technique."""
    try:
        data = await request.json()
        product = data.get("product", "")
        return web.json_response(
            {
                "tool": "bmad_cis_scamper",
                "product": product,
                "scamper": [
                    {
                        "letter": "S",
                        "action": "Substitute",
                        "prompt": f"What can we substitute in {product}?",
                    },
                    {
                        "letter": "C",
                        "action": "Combine",
                        "prompt": f"What can we combine {product} with?",
                    },
                    {
                        "letter": "A",
                        "action": "Adapt",
                        "prompt": f"What can we adapt to {product}?",
                    },
                    {"letter": "M", "action": "Modify", "prompt": f"How can we modify {product}?"},
                    {
                        "letter": "P",
                        "action": "Put to other uses",
                        "prompt": f"What other uses for {product}?",
                    },
                    {
                        "letter": "E",
                        "action": "Eliminate",
                        "prompt": f"What can we eliminate from {product}?",
                    },
                    {
                        "letter": "R",
                        "action": "Rearrange",
                        "prompt": f"How can we rearrange {product}?",
                    },
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_cis_worst_possible_idea")
async def tool_bmad_cis_worst_possible_idea(request: web.Request) -> web.Response:
    """Use Worst Possible Idea technique."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_cis_worst_possible_idea",
                "challenge": data.get("challenge", ""),
                "process": [
                    "1. Generate the worst possible ideas",
                    "2. Share and laugh about them",
                    "3. Identify what makes them bad",
                    "4. Flip the bad into good",
                    "5. Combine flipped ideas",
                ],
                "example_worst_ideas": [
                    "Make it intentionally confusing",
                    "Charge 100x the market price",
                    "Remove all documentation",
                ],
                "flipped": [
                    "Make it crystal clear and intuitive",
                    "Price competitively with clear value",
                    "Provide comprehensive documentation",
                ],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/bmad_cis_mind_mapping")
async def tool_bmad_cis_mind_mapping(request: web.Request) -> web.Response:
    """Create a mind map."""
    try:
        data = await request.json()
        return web.json_response(
            {
                "tool": "bmad_cis_mind_mapping",
                "central_topic": data.get("topic", ""),
                "branches": [
                    {"branch": "Main 1", "sub_branches": ["Sub 1.1", "Sub 1.2", "Sub 1.3"]},
                    {"branch": "Main 2", "sub_branches": ["Sub 2.1", "Sub 2.2"]},
                    {"branch": "Main 3", "sub_branches": ["Sub 3.1", "Sub 3.2", "Sub 3.3"]},
                ],
                "tools": ["XMind", "MindMeister", "Miro", "Figma"],
            }
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
