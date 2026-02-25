import httpx
import asyncio

async def main():
    system_version = 2  # change this to the version you want to activate

    url = f"http://localhost:8080/api/prompts/agent.system/{system_version}/activate"

    async with httpx.AsyncClient() as client:
        response = await client.put(url)
        response.raise_for_status()
        print(response.json())
        print(f"System version {system_version} activated")

asyncio.run(main())