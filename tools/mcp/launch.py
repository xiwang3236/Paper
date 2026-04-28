"""Launch the paper knowledge base MCP server."""

import asyncio
import os
from pathlib import Path

# Set working directory to tools/mcp/ so core imports work
os.chdir(Path(__file__).resolve().parent)

from server import main

if __name__ == "__main__":
    asyncio.run(main())
