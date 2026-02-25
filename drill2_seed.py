import httpx
import asyncio

async def main():
    url = "http://localhost:8080/api/prompts"

    # Agent System version 2
    payload = {
        "key": "agent.system",
        "content": "You are a concise assistant. Keep responses under 2 sentences.",
        "purpose": "terse",
        "owner": "eng",
    }

    # Agent System version 3
    # payload = {
    #     "key": "agent.system",
    #     "content": "You are a thorough assistant. Always explain your reasoning in detail.",
    #     "purpose": "verbose",
    #     "owner": "eng",
    # }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        print(response.json())

asyncio.run(main())