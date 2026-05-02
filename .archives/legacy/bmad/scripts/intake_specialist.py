import re

import yaml
from jsonschema import validate


# Since I am a language model, I can define the functions to perform the summarization,
# entity extraction, and workflow suggestion. In a real-world scenario, these would
# be calls to a dedicated language model API.


def summarize_request(request: str) -> str:
    """
    Summarizes the user's request.
    """
    # This is a simplified implementation. A real implementation would use a more
    # sophisticated summarization model.
    return f"The user wants to {request}"


def extract_entities(request: str) -> list:
    """
    Extracts entities from the user's request.

    Returns a list of structured entity objects with name, type, and value fields.
    Quoted substrings are treated as named entities of type 'literal'.
    """
    # This is a simplified implementation. A real implementation would use a more
    # sophisticated entity extraction model.
    entities = []
    # Find all words that are in quotes
    for match in re.finditer(r'"(.*?)"|\'(.*?)\'', request):
        value = match.group(1) or match.group(2)
        entities.append({"name": value, "type": "literal", "value": value})
    return entities


def extract_keywords(request: str) -> list:
    """
    Extracts keywords from the user's request.
    """
    # This is a simplified implementation. A real implementation would use a more
    # sophisticated keyword extraction model.
    return request.lower().split()


def suggest_workflow(request: str) -> str:
    """
    Suggests a workflow based on the user's request.
    """
    # This is a simplified implementation. A real implementation would use a more
    # sophisticated workflow suggestion model.
    if "create" in request and "agent" in request:
        return "create-agent-workflow"
    elif "repository" in request and "management" in request:
        return "repository-management-workflow"
    else:
        return "default-workflow"


def process_natural_language(request: str) -> str:
    """
    Processes a natural language request, summarizes it, and structures it into a YAML format.

    Args:
        request: The natural language request from the user.

    Returns:
        A YAML string with the structured output.
    """

    summarized_intent = summarize_request(request)

    entities = extract_entities(request)
    keywords = extract_keywords(request)
    suggested_workflow_name = suggest_workflow(request)

    output_data = {
        "original_request": request,
        "summarized_intent": summarized_intent,
        "entities": entities,
        "keywords": keywords,
        "suggested_workflow": suggested_workflow_name,
    }

    with open("bmad/schemas/intake_schema.yml") as schema_file:
        schema = yaml.safe_load(schema_file)

    validate(instance=output_data, schema=schema)

    return yaml.dump(output_data)


if __name__ == "__main__":
    test_request = "Please create a new agent called 'Test Agent'"
    try:
        yaml_output = process_natural_language(test_request)
        print(yaml_output)
    except ValueError as e:
        print(f"Error: {e}")
