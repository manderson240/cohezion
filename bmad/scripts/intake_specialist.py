import yaml
from jsonschema import validate


def validate_intent(original_request: str, summarized_intent: str) -> bool:
    """
    Validates that the summarized intent preserves the core meaning
    of the original request.

    Args:
        original_request: The original natural language request.
        summarized_intent: The summarized intent.

    Returns:
        True if the intent is preserved, False otherwise.
    """

    # This is a placeholder for a call to a language model to compare the semantic
    # similarity of the two strings.
    # In a real implementation, this would use a sentence similarity model.
    # For now, we'll use a simple keyword-based check.

    original_keywords = set(original_request.lower().split())
    summarized_keywords = set(summarized_intent.lower().split())

    # Check if at least 50% of the keywords are shared
    return (
        len(original_keywords.intersection(summarized_keywords))
        / len(original_keywords)
        >= 0.5
    )


def process_natural_language(request: str) -> str:
    """
    Processes a natural language request, summarizes it,
    and structures it into a YAML format.

    Args:
        request: The natural language request from the user.

    Returns:
        A YAML string with the structured output.
    """

    # 1. Summarize the request (placeholder for a call to a language model)
    summarized_intent = f"Summary of: {request}"  # Placeholder

    # 2. Validate the intent
    if not validate_intent(request, summarized_intent):
        raise ValueError(
            "Intent validation failed: The summarized intent"
            " does not seem to preserve the original meaning."
        )

    # 3. Extract entities and keywords (placeholder)
    entities = [
        {"name": "example_entity", "type": "example_type", "value": "example_value"}
    ]
    keywords = ["example_keyword1", "example_keyword2"]

    # 4. Structure the output
    output_data = {
        "original_request": request,
        "summarized_intent": summarized_intent,
        "entities": entities,
        "keywords": keywords,
    }

    # 5. Validate the output against the schema
    with open("bmad/schemas/intake_schema.yml") as schema_file:
        schema = yaml.safe_load(schema_file)

    validate(instance=output_data, schema=schema)

    # 6. Return the YAML string
    return yaml.dump(output_data)


if __name__ == "__main__":
    test_request = (
        "We need an intake specialist that converts the natural"
        " language request to the orchestratory to assemble a"
        " squad of agents to execute a workflow"
    )
    try:
        yaml_output = process_natural_language(test_request)
        print(yaml_output)
    except ValueError as e:
        print(f"Error: {e}")
