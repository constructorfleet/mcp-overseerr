from dotenv import load_dotenv
import os
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
env_fp = os.path.join(project_dir, ".env")
load_dotenv(env_fp)


import asyncio
import logging
from typing import Optional
from fastmcp import FastMCP

from . import tools


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-overseerr")

# Check for required environment variables
api_key = os.getenv("OVERSEERR_API_KEY")
url = os.getenv("OVERSEERR_URL")

if not api_key or not url:
    raise ValueError(
        f"OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required. Working directory: {os.getcwd()}"
    )

app = FastMCP("mcp-overseerr")

status_tool_handler = tools.StatusToolHandler()
movie_requests_tool_handler = tools.MovieRequestsToolHandler()
tv_requests_tool_handler = tools.TvRequestsToolHandler()





@app.tool(
    name="overseerr_get_status",
    description="Get the current status and version of the Overseerr server.",
    tags={"overseerr", "status"},
)
async def overseerr_status() -> str:
    """Get the current status and version of the Overseerr server."""
    result = await status_tool_handler.run_tool({})
    return result[0].text if result else "No status available"





@app.tool(
    name="overseerr_get_movie_requests",
    description="Get a list of movie requests from Overseerr. Can be filtered by status (e.g., 'approved', 'pending') and start date.",
    tags={"overseerr", "movie", "requests"},
)
async def overseerr_movie_requests(
    status: Optional[str] = None, start_date: Optional[str] = None
) -> str:
    """Get a list of movie requests from Overseerr."""
    args = {"status": status, "start_date": start_date}
    result = await movie_requests_tool_handler.run_tool(args)
    return result[0].text if result else "No movie requests found"

@app.tool(
    name="overseerr_get_tv_requests",
    description="Get a list of TV show requests from Overseerr. Can be filtered by status (e.g., 'approved', 'pending') and start date.",
    tags={"overseerr", "tv", "requests"},
)
async def overseerr_tv_requests(
    status: Optional[str] = None, start_date: Optional[str] = None
) -> str:
    """Get a list of TV show requests from Overseerr."""
    args = {"status": status, "start_date": start_date}
    result = await tv_requests_tool_handler.run_tool(args)
    return result[0].text if result else "No TV requests found"

def main():
    """Main entry point for the overseerr-mcp server."""
    app.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
        path="/mcp",
        log_level="debug"
    )


if __name__ == "__main__":
    main()
