# Specification: Gemini Deep Research Integration

## Overview
This track implements the integration of the Gemini Deep Research API into the Cohezion orchestration layer. Deep Research provides autonomous web navigation, multi-step synthesis, and cited reports, which will replace or enhance our current "Look Outward" research capabilities.

## Functional Requirements
- **Deep Research Provider**: Implement a `DeepResearchProvider` in `src/cohezion/providers/` that interfaces with the Google Interactions API.
- **Asynchronous Execution**: Support asynchronous background execution with status polling and result retrieval.
- **MCP Integration**: Enable MCP tool support within Deep Research calls to allow grounding against local vault data.
- **Autonomous Research expert**: Create a new "Research" expert stream that utilizes Deep Research for complex discovery tasks.
- **Reporting**: Automatically persist Deep Research cited reports into the Obsidian Knowledge Vault.

## Non-Functional Requirements
- **Cost Management**: Implement budget tracking for Deep Research calls (est. $1-$7 per task).
- **Transparency**: Log "Thinking Summaries" to the telemetry stream for real-time observability in the Anima Dashboard.

## Acceptance Criteria
- [ ] `DeepResearchProvider` successfully initializes a background interaction.
- [ ] Agent can poll status and retrieve completed citied reports.
- [ ] Deep Research findings are automatically stored as `.md` files in the vault's `research/` directory.
- [ ] Thinking summaries are emitted as `FlumeJourneyEvents` to the telemetry bus.
