from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="/opt/homebrew/bin/uv",  # Executable
    args=["run", "--with", "mcp", "mcp", "run", "./server.py"],  # Properly split args
    env={"ALPACA_API_KEY": "", "ALPACA_API_SECRET": ""}  # Use dictionary for env variables
)


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            resource = await session.read_resource("account://account_summary")
            print(f"{resource=}") # raw read_resource() results
            print(f"   🔗 URI: {resource.contents[0].uri}")
            print(f"   📜 Result: {resource.contents[0].text}")
            print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())