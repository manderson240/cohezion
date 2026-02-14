# Compound Engineering Usage Examples

## Basic Usage Examples

### Simple Feature Implementation
```bash
# Create a basic REST API endpoint
opencode -m qwen3-coder-256k "Create a REST API endpoint for user management with GET, POST, PUT, DELETE methods"

# Result: Uses only the core coding model for simple implementation
```

### Complex Feature Development
```bash
# Build a complete authentication system
opencode "Create a full authentication system with JWT tokens, password hashing, email verification, and role-based access control"

# Result: Uses compound engineering to orchestrate multiple models:
# 1. gpt-oss-256k analyzes requirements and plans architecture
# 2. qwen3-coder-256k designs the system
# 3. glm-4.7-flash-256k implements the code
# 4. Models integrate and optimize the solution
```

### System Architecture Design
```bash
# Design a microservices architecture
opencode "Design a scalable microservices architecture for an e-commerce platform with inventory management, order processing, and payment integration"

# Result: Uses analysis and planning models to create comprehensive architecture
```

### Algorithm Optimization
```bash
# Optimize a sorting algorithm
opencode "Optimize this quicksort implementation for large datasets with better pivot selection and parallel processing"

# Result: Uses mathematical reasoning models for optimization
```

## Advanced Usage Examples

### Full Application Development
```bash
# Build a complete web application
opencode "Create a full-stack web application for task management with real-time collaboration, file uploads, and team features"

# Workflow:
# 1. Analysis: System requirements and architecture planning
# 2. Design: Database schema and API design
# 3. Implementation: Frontend and backend development
# 4. Integration: Connect all components
# 5. Testing: Quality assurance and optimization
```

### Enterprise Solution
```bash
# Build enterprise-grade solution
opencode "Create an enterprise document management system with version control, access control, workflow automation, and audit trails"

# Workflow:
# 1. System analysis and requirements gathering
# 2. Architecture design with scalability considerations
# 3. Component implementation with specialized models
# 4. Integration and testing
# 5. Performance optimization
```

### Specialized Domain
```bash
# Financial application development
opencode "Create a financial trading platform with real-time data processing, risk management, and automated trading algorithms"

# Uses specialized models for:
# - Mathematical computations (phi4-256k)
# - Financial domain knowledge (gemma3-4b-256k)
# - System design (gpt-oss-256k)
# - Implementation (qwen3-coder-256k)
```

## Memory Management Examples

### Low Memory Scenario
```bash
# When memory is constrained
# The system automatically:
# 1. Unloads unused models
# 2. Prioritizes core models
# 3. Uses more efficient model combinations
# 4. Provides warnings when approaching limits
```

### High Memory Availability
```bash
# When memory is abundant
# The system can:
# 1. Load multiple specialized models
# 2. Run parallel tasks
# 3. Cache more results
# 4. Use more comprehensive model combinations
```

## Performance Optimization Examples

### Code Optimization
```bash
# Optimize existing code
opencode "Optimize this Python code for better performance and memory usage"

# Uses phi4-256k for mathematical optimization
# and qwen3-coder-256k for implementation
```

### Database Optimization
```bash
# Optimize database queries
opencode "Optimize these SQL queries for better performance with large datasets"

# Uses analytical models for query analysis
# and coding models for implementation
```

## Monitoring and Debugging

### System Monitoring
```bash
# Check system status
opencode "Show system resource usage and model activity"

# Provides:
# - Current memory usage
# - Active models
# - Task progress
# - Performance metrics
```

### Debugging Assistance
```bash
# Debug complex issues
opencode "Debug this complex issue with database connections and API timeouts"

# Uses multiple models to:
# 1. Analyze the problem
# 2. Identify root causes
# 3. Propose solutions
# 4. Implement fixes
```

## Best Practices

### Task Complexity Guidelines
- **Simple tasks**: Use single models
- **Medium tasks**: Use 2-3 models
- **Complex tasks**: Use full compound system
- **Critical tasks**: Use all available models with redundancy

### Memory Management
- Monitor available memory regularly
- Unload unused models promptly
- Prioritize core models
- Use efficient model combinations

### Performance Optimization
- Use appropriate model combinations
- Cache successful results
- Monitor execution times
- Optimize model parameters

### Error Handling
- Use fallback models
- Implement retry logic
- Monitor for failures
- Provide clear error messages

## Troubleshooting

### Common Issues
1. **Memory Pressure**: System unloads models automatically
2. **Model Failures**: Fallback to backup models
3. **Performance Issues**: Optimize model combinations
4. **Network Issues**: Local processing fallback

### Solutions
- Check memory usage: `free -h`
- Monitor models: `ollama ps`
- Review logs: `journalctl --user -u smart-loader.service`
- Restart services if needed

## Configuration Examples

### Custom Model Selection
```bash
# Force specific model combination
export OPENCODE_COMPOUND_MODELS="qwen3-coder-256k,gpt-oss-256k,glm-4.7-flash-256k"
opencode "Your task here"
```

### Memory Constraints
```bash
# Set memory limits
export OPENCODE_MEMORY_LIMIT=80
opencode "Your task here"
```

### Performance Tuning
```bash
# Adjust performance parameters
export OPENCODE_TEMPERATURE=0.3
export OPENCODE_MAX_TOKENS=8192
opencode "Your task here"
```

This compound engineering system provides intelligent orchestration of multiple specialized models to handle complex software engineering tasks efficiently while maintaining system stability through smart memory management.