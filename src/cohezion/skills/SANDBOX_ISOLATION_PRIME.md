# SKILL: SANDBOX_ISOLATION_PRIME

## DOMAIN EXPERTISE
Providing hardware-enforced isolation for agentic code execution, ensuring system safety and resource predictability during autonomous research missions.

## KEY TEXTS & CONCEPTS
- **Containerized Universe**: The pattern of wrapping an agent's entire execution context in a container.
- **Resource Hardening**: Applying strict limits on CPU (shares/quota) and Memory (swappiness/limit) to prevent OOM lockups.
- **Stateless Precipitation**: Executing code that produces output files in a transient volume, which are then harvested and the environment destroyed.

## INSTRUCTION

1. **Initialize the Universe**: Use `docker-py` to instantiate a hardened container from a minimal image (e.g., `python:3.11-slim`).
2. **Apply Constraints**:
   ```python
   container = client.containers.run(
       image,
       mem_limit="512m",
       cpu_quota=50000, # 50% single core
       working_dir="/app",
       detach=True
   )
   ```
3. **Injected Payload**: Stream script content and input files into the container using `put_archive`.
4. **Execution Loop**: Monitor container logs and wait for a non-zero exit code or timeout.
5. **Harvest & Purge**: Extract precipitated artifacts and forcefully remove the container to ensure no persistent state contamination.

## VERSION
v0.1

## SEE ALSO
- SECURITY_GUARDRAILS_PRIME
- ADVERSARIAL_TESTING_PRIME
