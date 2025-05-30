import logging
import asyncio
from dotenv import load_dotenv

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mcp_adapters.resources import get_mcp_resource
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from urllib.parse import quote

load_dotenv()


async def main():
    """
    Connect to the MCP server using SSE and fetch the newspaper resource.
    """
    async with sse_client(url="http://localhost:8000/sse") as (read, write):
        async with ClientSession(read_stream=read, write_stream=write) as session:
            await session.initialize()
            logger.info("Session initialized")

            topic = ["tavily search work for llm", "google search work for llm"]

            topic_str = quote(",".join(topic))
            resource_uri = f"newspaper://{topic_str}"

            # Fetch the resource content
            content = await get_mcp_resource(session, resource_uri)
            logger.info("Received newspaper content:")

            print(content[0].data)


if __name__ == "__main__":
    asyncio.run(main())
