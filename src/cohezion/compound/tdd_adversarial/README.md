# TDD and Adversarial Review Integration

This module provides persistent Test-Driven Development (TDD) and Multiperspective Adversarial Review capabilities for the Compound Engineering system.

## Components

### 1. TDD Integration (`tdd_integration.py`)
Provides test-driven development capabilities:
- Automatic test execution before and after compound engineering operations
- Test coverage tracking and reporting
- Test generation from specifications
- Feedback to skill refinement based on test performance
- Red-green-refactor cycle management

### 2. Adversarial Review System (`adversarial_review.py`)
Provides multiperspective adversarial review:
- Multiple review perspectives: Security, Performance, Reliability, Usability, Maintainability, Compliance, Innovation, Ethics
- Conflict detection between perspectives
- Insight synthesis from diverse viewpoints
- Historical tracking of review sessions
- Feedback to skill refinement based on review outcomes

### 3. Coordinator (`coordinator.py`)
Integrates TDD and Adversarial Review systems:
- Pre-engineering checks (TDD + initial review)
- Post-engineering checks (comprehensive TDD + full review)
- Combined feedback for skill refinement
- Integrated metrics and reporting
- Engineering quality assessment

### 4. Daemon Components (`daemon/`)
Provides persistent operation capabilities:
- Automatic git worktree creation for isolated work
- Workflow initialization with TDD and review preparation
- Session management and state persistence

## Usage

### Direct Component Usage
```python
from cohezion.compound.tdd_adversarial import get_tdd_integration, get_adversarial_review_system, get_tdd_adversarial_coordinator

# Get TDD integration
tdd = get_tdd_integration()
await tdd.run_tests("session_001")

# Get Adversarial Review System
review = get_adversarial_review_system()
session = await review.run_full_adversarial_review("session_001")

# Get Coordinator
coordinator = get_tdd_adversarial_coordinator()
pre_checks = await coordinator.run_pre_engineering_checks("session_001")
post_checks = await coordinator.run_post_engineering_checks("session_001")
feedback = coordinator.get_integration_feedback_for_skill_refinement("session_001")
```

### Automatic Initialization
The system is automatically initialized at the start of each session through Opencode hooks:
- `.opencode/hooks/init/00_setup_worktree.sh` - Creates isolated git worktrees
- `.opencode/hooks/init/01_init_compound_engineering.sh` - Initializes TDD and Adversarial Review environments

## Integration Points

The system integrates with the existing Compound Engineering system through:

1. **Skill Refinement**: Both TDD and Adversarial Review systems provide `SkillRefinementInput` objects to improve skills
2. **Session Management**: Works with the existing session manager to enhance engineering cycles
3. **Metrics Systems**: Contributes to the overall metrics collection and reporting
4. **Feedback Loops**: Enhances existing feedback mechanisms with TDD and review insights

## Perspectives Implemented

The Adversarial Review System includes these perspectives:

- **Security**: Focuses on vulnerabilities, threat models, attack surfaces
- **Performance**: Analyzes bottlenecks, scalability issues, resource efficiency
- **Reliability**: Examines failure modes, recovery patterns, fault tolerance
- **Usability**: Evaluates developer experience, API clarity, documentation quality
- **Maintainability**: Assesses code complexity, technical debt, refactoring needs
- **Compliance**: Checks adherence to standards, policies, best practices
- **Innovation**: Looks for opportunities for improvement and novel approaches
- **Ethics**: Considers ethical implications and responsible AI considerations

## TDD Integration Features

- Test execution before/after engineering operations
- Coverage tracking and reporting
- Test generation from specifications
- Feedback for skill refinement based on test effectiveness
- Support for unit, integration, functional, performance, and security tests

## Configuration

The system works with the existing Cohezion configuration system and can be customized through:
- Environment variables
- Configuration files in `src/cohezion/config/`
- Hook system configuration in `.opencode/hooks/`

## Requirements

- Python 3.13+
- pytest for test execution
- coverage.py for coverage reporting
- Git for worktree functionality

## Future Enhancements

1. **Predictive TDD**: Use historical data to predict which tests are likely to fail
2. **Adaptive Perspective Weighting**: Dynamically adjust perspective importance based on context
3. **Advanced Conflict Resolution**: Use AI to suggest resolutions for perspective conflicts
4. **Integration with External CI/CD**: Connect to external continuous integration systems
5. **Enhanced Test Generation**: Use LLMs to generate more sophisticated test cases
6. **Perspective-Specific Skill Models**: Develop specialized skills for each review perspective
