import asyncio
import json
import os
from cohezion.swarm.providers.ollama_provider import OllamaProvider

async def generate_task():
    print("Initializing Ollama provider...")
    provider = OllamaProvider(config={"base_url": "http://localhost:11434", "timeout": 600})
    
    prompt = """
    Create a highly advanced ARC-AGI style benchmark task.
    Rule: Each red object (2) moves towards the nearest blue object (1) until they touch, then the red object turns green (3).
    Mechanic: OMIT the training example that explains what happens if multiple red objects are equidistant.
    Correct Answer: "Insufficient Information".
    
    Respond ONLY with a valid JSON object matching this schema:
    {
      "input": "Question: [Describe patterns]\\nExample 1: In [[...]] Out [[...]]\\nExample 2: In [[...]] Out [[...]]\\nTest Input: [[...]]\\n\\nOptions:\\n['[[...]]', '[[...]]', '[[...]]', 'Insufficient Information']\\n",
      "output": "Insufficient Information"
    }
    """
    
    print("Generating...")
    # Use phi3:mini for speed
    result = await provider.generate(model="phi3:mini", prompt=prompt, max_tokens=1024)
    
    print("\nRESULT:")
    print(result.response)
    
    with open("minimal_task.json", "w") as f:
        f.write(result.response)
    
    await provider.close()

if __name__ == "__main__":
    asyncio.run(generate_task())
