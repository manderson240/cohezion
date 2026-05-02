import asyncio
import sys
sys.path.insert(0, '/home/mike-anderson/dev/cohezion/src')

# We need to import the module without running main()
import importlib.util
spec = importlib.util.spec_from_file_location('compound_server', '/home/mike-anderson/dev/cohezion/src/cohezion/mcp/compound_server.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

async def main():
    tools = await mod.mcp.list_tools()
    print('tools count:', len(tools))
    for t in tools:
        print(' -', t.name)

asyncio.run(main())
