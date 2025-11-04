class ContextEngineeringInfrastructure:
    def __init__(self):
        self._tools = {}

    def register_tool(self, name, tool):
        self._tools[name] = tool

    def execute_tool(self, name, **kwargs):
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name](**kwargs)

    def list_tools(self):
        return list(self._tools.keys())
