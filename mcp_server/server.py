import logging
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import glob
from urllib.parse import unquote

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("gpt-newspaper-mcp")

# Your MasterAgent import and usage assumed correct
from backend.langgraph_agent import MasterAgent


@mcp.resource(uri="newspaper://{topic}")
def newspaper_resource(topic: str):
    """
    MCP resource that generates a newspaper and exposes the resulting HTML file.
    Args:
        topic: A comma-separated string of topics to be included in the newspaper.
    Returns:
        The HTML content of the generated newspaper.
    """
    # Decode URL-encoded string and split into list
    decoded_topic = unquote(topic)
    topic_list = [t.strip() for t in decoded_topic.split(",") if t.strip()]

    logger.info(f"Received topic list: {topic_list} (length: {len(topic_list)})")

    agent = MasterAgent()
    layout = "layout_1.html"
    agent.run(topic_list, layout)
    
    # Get all HTML files in the output directory
    output_dir = agent.output_dir
    html_files = glob.glob(os.path.join(output_dir, "*.html"))
    
    # Combine all HTML content
    combined_content = []
    for html_file in html_files:
        logger.info(f"Reading content from: {html_file}")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            combined_content.append(content)
    
    # Join all content with a separator
    final_content = "\n\n".join(combined_content)
    logger.info(f"Combined content from {len(html_files)} files")
    
    return final_content


if __name__ == "__main__":
    # Run MCP server with SSE transport (matches client)
    mcp.run(transport="sse")
