# Compound Engineering Setup for OpenCode with Smart Loading/Offloading

## System Overview
- **RAM**: 125GB total, 77GB available
- **GPU**: AMD RYZEN AI MAX+ 395 with 512MB VRAM + 128GB GTT (Unified Memory)
- **CPU**: AMD Ryzen AI Max+ 395 (16 cores / 32 threads)
- **Context Window**: 256K tokens (optimized for compound engineering)

## Model Architecture for Compound Engineering

### Core Orchestration Models (High Context)
1. **qwen3-coder-256k** - Primary coding specialist (18GB)
2. **gpt-oss-256k** - Analysis and planning (18GB)  
3. **glm-4.7-flash-256k** - Fast coding execution (23GB)

### Specialized Small Language Models (High Context)
4. **phi4-256k** - Specialized task execution (3GB)
5. **gemma3-4b-256k** - Specialized task execution (2GB)
6. **qwen2.5-coder-14b-256k** - Mid-tier coding (7GB)

## Smart Loading/Offloading Strategy

### Memory Management
```bash
# System memory layout
Total RAM: 125GB
- System usage: ~8GB
- Available for models: ~117GB
- Safety buffer: ~10GB
- Models can use: ~107GB
```

### Dynamic Loading Strategy

#### Phase 1: Core Models (Always Loaded)
- **qwen3-coder-256k** - Always resident (18GB)
- **gpt-oss-256k** - Always resident (18GB)
- **Total**: 36GB

#### Phase 2: Task-Specific Loading
Based on detected task type:
- **Coding tasks**: Load glm-4.7-flash-256k (23GB)
- **Analysis tasks**: Load phi4-256k (3GB) + gemma3-4b-256k (2GB)
- **Complex tasks**: Load qwen2.5-coder-14b-256k (7GB)

#### Phase 3: Smart Offloading
- Monitor memory usage every 30 seconds
- Unload models not used in last 5 minutes
- Keep core models resident
- Use GGUF quantization for smaller variants when possible

## Compound Engineering Workflow

### Step 1: Task Detection
```python
def detect_task_type(context):
    """Analyze context to determine optimal model combination"""
    if "implement" in context or "build" in context:
        return "coding"
    elif "analyze" in context or "plan" in context:
        return "analysis"
    elif "optimize" in context or "refactor" in context:
        return "optimization"
    else:
        return "general"
```

### Step 2: Model Selection
```python
def select_models(task_type, complexity):
    """Select optimal model combination based on task"""
    base_models = ["qwen3-coder-256k", "gpt-oss-256k"]
    
    if task_type == "coding":
        if complexity == "high":
            return base_models + ["glm-4.7-flash-256k"]
        else:
            return base_models + ["qwen2.5-coder-14b-256k"]
    elif task_type == "analysis":
        return base_models + ["phi4-256k", "gemma3-4b-256k"]
    else:
        return base_models
```

### Step 3: Compound Execution
```python
def compound_engine_execute(task, context):
    """Execute compound engineering workflow"""
    # Step 1: Analysis and planning
    analysis_models = select_models("analysis", "high")
    plan = execute_models(analysis_models, f"Plan {task}", context)
    
    # Step 2: Break down into sub-tasks
    sub_tasks = break_down_tasks(plan)
    
    # Step 3: Execute with specialized models
    results = []
    for sub_task in sub_tasks:
        models = select_models(detect_task_type(sub_task), "medium")
        result = execute_models(models, sub_task, context)
        results.append(result)
    
    # Step 4: Integration and optimization
    integration_models = ["qwen3-coder-256k", "gpt-oss-256k"]
    final_result = execute_models(integration_models, "Integrate results", context)
    
    return final_result
```

## Memory Usage Projections

### Worst Case Scenario (All Models Loaded)
- qwen3-coder-256k: 18GB
- gpt-oss-256k: 18GB  
- glm-4.7-flash-256k: 23GB
- phi4-256k: 3GB
- gemma3-4b-256k: 2GB
- qwen2.5-coder-14b-256k: 7GB
- **Total**: 71GB

### Typical Usage (3-4 Models)
- Core models: 36GB
- 1-2 specialized models: 5-30GB
- **Typical range**: 41-66GB

### Safety Margin
- Available RAM: 77GB
- Typical usage: 50-60GB
- **Safety buffer**: 17-27GB

## Implementation Scripts

### Smart Model Loader
```bash
#!/bin/bash
# smart_loader.sh - Intelligent model loading/offloading

MODEL_DIR="/root/.ollama"
CORE_MODELS=("qwen3-coder-256k" "gpt-oss-256k")
SPECIALIZED_MODELS=(
    "glm-4.7-flash-256k"
    "phi4-256k" "gemma3-4b-256k"
    "qwen2.5-coder-14b-256k"
)

# Check available memory
check_memory() {
    free_mem=$(free -g | awk 'NR==2{print $7}')
    echo "Available memory: ${free_mem}GB"
    return $free_mem
}

# Load core models
load_core_models() {
    for model in "${CORE_MODELS[@]}"; do
        if ! ollama ps | grep -q "$model"; then
            echo "Loading core model: $model"
            ollama pull "$model" &
        fi
    done
}

# Smart model loading based on task
load_specialized_models() {
    local task_type=$1
    local complexity=$2
    
    case $task_type in
        "coding")
            if [ "$complexity" = "high" ]; then
                load_model "glm-4.7-flash-256k"
            else
                load_model "qwen2.5-coder-14b-256k"
            fi
            ;;
        "analysis")
            load_model "phi4-256k"
            load_model "gemma3-4b-256k"
            ;;
    esac
}

# Unload unused models
unload_unused_models() {
    # Unload models not used in last 5 minutes
    for model in "${SPECIALIZED_MODELS[@]}"; do
        if ! ollama ps | grep -q "$model"; then
            echo "Model $model already unloaded"
        else
            # Check last activity
            last_activity=$(ollama ps | grep "$model" | awk '{print $NF}')
            if [ "$last_activity" = "Forever" ]; then
                echo "Model $model is active"
            else
                echo "Unloading unused model: $model"
                ollama rm "$model" &
            fi
        fi
    done
}

# Main execution
main() {
    local task_type=$1
    local complexity=$2
    
    # Always load core models
    load_core_models
    
    # Load specialized models based on task
    load_specialized_models "$task_type" "$complexity"
    
    # Monitor memory and unload if needed
    while true; do
        available_mem=$(check_memory)
        if [ $available_mem -lt 20 ]; then
            echo "Low memory! Unloading unused models..."
            unload_unused_models
        fi
        sleep 30
    done
}

main "$1" "$2"