# Compound Engineering Usage Examples

## Quick Start Guide

### 1. Model Selection
```bash
# Select optimal model for a task
./src/cohezion/skills/cohezion_mcp.py execute model_selection coding 7 256000
```

### 2. Skill Execution
```bash
# Execute a registered skill
./src/cohezion/skills/cohezion_mcp.py execute skill_execution SUBAGENT_DELEGATION_PRIME
```

### 3. Workflow Orchestration
```bash
# Run a complete workflow
./src/cohezion/skills/cohezion_mcp.py execute workflow_orchestration compound_engineering_workflow '[{"name": "analysis", "description": "Code analysis"}]'
```

## Integration Examples

### A. Complete Engineering Session

```bash
#!/bin/bash

# 1. Select model
MODEL_INFO=$(./src/cohezion/skills/cohezion_mcp.py execute model_selection coding 8 256000)
MODEL=$(echo "$MODEL_INFO" | jq -r '.recommended_model')
echo "Selected model: $MODEL"

# 2. Execute skill
SKILL_RESULT=$(./src/cohezion/skills/cohezion_mcp.py execute skill_execution SUBAGENT_DELEGATION_PRIME)
echo "Skill executed: $SKILL_RESULT"

# 3. Manage context
CONTEXT_RESULT=$(./src/cohezion/skills/cohezion_mcp.py execute context_management add project '{
  "engineering_system": "compound_256k",
  "models_used": "$MODEL"
}')
echo "Context managed: $CONTEXT_RESULT"

# 4. Run workflow
echo "Running complete workflow..."
WORKFLOW_RESULT=$(./src/cohezion/skills/cohezion_mcp.py execute workflow_orchestration compound_engineering_workflow '[{"name": "complete_engineering", "description": "Complete engineering workflow"}]')
echo "Workflow result: $WORKFLOW_RESULT"
```

### B. Real-time Model Selection

```python
import subprocess
import json

def select_model_for_task(task_type: str, complexity: int = 5):
    """Select optimal model based on task requirements"""
    result = subprocess.run([
        "./src/cohezion/skills/cohezion_mcp.py",
        "execute",
        "model_selection",
        task_type,
        str(complexity),
        "256000"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise Exception(f"Model selection failed: {result.stderr}")

# Usage
model_info = select_model_for_task("coding", 8)
print(f"Recommended model: {model_info['recommended_model']}")
```

## Advanced Usage

### 1. Custom Workflow Creation

```json
{
  "my_custom_workflow": {
    "name": "my_custom_workflow",
    "description": "Custom workflow for specific engineering tasks",
    "steps": [
      {
        "name": "pre_analysis",
        "tool": "skill_execution",
        "parameters": {
          "skill_name": "CODE_REFACTORING_PRIME",
          "context": "optimization"
        }
      },
      {
        "name": "model_selection",
        "tool": "model_selection",
        "parameters": {
          "task_type": "optimization",
          "complexity": 9,
          "context_needs": 256000
        }
      },
      {
        "name": "implementation",
        "tool": "skill_execution",
        "parameters": {
          "skill_name": "OPTIMIZATION_ALGORITHMS_PRIME",
          "context": "performance"
        }
      }
    ],
    "dependencies": {
      "requires_models": ["qwen3-coder-256k:latest"],
      "requires_skills": ["CODE_REFACTORING_PRIME", "OPTIMIZATION_ALGORITHMS_PRIME"],
      "context_window": 256000
    }
  }
}
```

### 2. Context Management Patterns

```python
# Add project context
context_result = subprocess.run([
    "./src/cohezion/skills/cohezion_mcp.py",
    "execute",
    "context_management",
    "add",
    "project",
    json.dumps({
        "project_name": "compound_engineering",
        "models_used": ["qwen3-coder-256k", "gemma3-4b-256k"],
        "current_phase": "development",
        "complexity": 8
    })
], capture_output=True, text=True)

# Retrieve context
context_result = subprocess.run([
    "./src/cohezion/skills/cohezion_mcp.py",
    "execute",
    "context_management",
    "retrieve",
    "project"
], capture_output=True, text=True)
```

## Performance Tips

### 1. Model Selection Strategy
- **Low complexity (1-3)**: Use gemma3-4b-256k for faster responses
- **Medium complexity (4-6)**: Use phi4-256k for balanced performance
- **High complexity (7-8)**: Use gpt-oss-256k for comprehensive analysis
- **Maximum complexity (9-10)**: Use qwen3-coder-256k for advanced tasks

### 2. Context Management
- **Short sessions**: Keep context minimal for faster responses
- **Long sessions**: Use context management to maintain state
- **Project-wide**: Store persistent context for team collaboration

### 3. Error Handling
```python
import subprocess
import json
import time

def execute_with_retry(command, max_retries=3, delay=1):
    """Execute command with retry logic"""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                raise Exception(f"Command failed: {result.stderr}")
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2  # Exponential backoff
```

## Integration with OpenCode

### Configuration
```json
{
  "models": {
    "compound_engineering": {
      "description": "Compound engineering system",
      "models": ["qwen3-coder-256k:latest"],
      "orchestration": "smart_context_switching",
      "tools": ["skill_execution", "workflow_orchestration", "context_management"]
    }
  }
}
```

### Usage in OpenCode
```bash
# Direct OpenCode usage
opencode --model compound_engineering "Write a complex function"

# With skill execution
opencode --model compound_engineering --tool skill_execution "SUBAGENT_DELEGATION_PRIME" "complex task"
```

## Monitoring and Debugging

### 1. System Status
```bash
# Check available models
curl -s http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("256k")) | .name'

# Check MCP server status
./src/cohezion/skills/cohezion_mcp.py list_tools
```

### 2. Performance Metrics
- **Response times**: Monitor execution durations
- **Model usage**: Track which models are selected
- **Context efficiency**: Measure context utilization
- **Error rates**: Monitor failure patterns

## Best Practices

### 1. Model Selection
- Start with lower complexity models for initial exploration
- Escalate to higher complexity models for critical tasks
- Use context management to preserve state across sessions

### 2. Skill Usage
- Use skills for repetitive tasks
- Create custom skills for domain-specific operations
- Leverage the skill registry for discovery

### 3. Workflow Design
- Break complex tasks into smaller steps
- Use dependencies to ensure proper execution order
- Implement error handling at each step

### 4. Context Management
- Store project-wide context for team collaboration
- Use temporal context for session-specific information
- Implement context cleanup to manage memory usage

## Troubleshooting

### Common Issues

1. **Model not found**: Ensure models are properly loaded in Ollama
2. **Skill execution failed**: Verify skill paths in registry
3. **Workflow errors**: Check step dependencies and parameters
4. **Context issues**: Validate context data format

### Debug Commands
```bash
# List all available models
ollama list

# Check MCP server logs
./src/cohezion/skills/cohezion_mcp.py list_tools

# Test individual components
./src/cohezion/skills/cohezion_mcp.py execute skill_execution AutomationTestFixed
```

This integration provides a powerful foundation for AI-assisted engineering with sophisticated orchestration capabilities.