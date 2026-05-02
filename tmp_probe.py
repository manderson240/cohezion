from fastmcp import FastMCP
m = FastMCP('test')

@m.tool()
async def foo():
    return {}

import asyncio
async def main():
    tools = await m.list_tools()
    print('tools count:', len(tools))
    for t in tools:
        print('tool name:', t.name)

asyncio.run(main())
