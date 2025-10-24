# MCP server for Overseerr

MCP server to interact with Overseerr API for movie and TV show requests management.

<!-- Badge will be added once published -->

## Components

### Tools

The server implements multiple tools to interact with Overseerr:

- overseerr_get_status: Get the status of the Overseerr server
- overseerr_get_movie_requests: Get the list of all movie requests that satisfies the filter arguments
- overseerr_get_tv_requests: Get the list of all TV show requests that satisfies the filter arguments

#### overseerr_movie_requests response structure

The JSON payload returned by `overseerr_movie_requests` is built by
[`MovieRequestsToolHandler.get_movie_requests`](src/overseerr_mcp/tools.py)
and always uses the following fields:

- `title`: Human readable movie name resolved from Overseerr.
- `media_availability` values: `UNKNOWN`, `PENDING`, `PROCESSING`, `PARTIALLY_AVAILABLE`, `AVAILABLE`.
- `request_date` (ISO 8601 creation timestamp from Overseerr).

Movie request example:

```json
[
  {
    "title": "Dune",
    "media_availability": "PENDING",
    "request_date": "2024-05-01T12:34:56.000Z"
  }
]
```

#### overseerr_tv_requests response structure

The JSON payload returned by `overseerr_tv_requests` is created via
[`TvRequestsToolHandler.get_tv_requests`](src/overseerr_mcp/tools.py) and exposes:

- `tv_title`: Human readable series name.
- `tv_title_availability` and `tv_season_availability` share the same status options as movie requests (`UNKNOWN`, `PENDING`, `PROCESSING`, `PARTIALLY_AVAILABLE`, `AVAILABLE`).
- `tv_season` is formatted as `SXX` to mirror Overseerr numbering.
- `tv_episodes` is a list of episode objects containing `episode_number` and `episode_name`.
- `request_date` (ISO 8601 creation timestamp from Overseerr).

TV request example:

```json
[
  {
    "tv_title": "Avatar: The Last Airbender",
    "tv_title_availability": "AVAILABLE",
    "tv_season": "S01",
    "tv_season_availability": "AVAILABLE",
    "tv_episodes": [
      {
        "episode_number": "01",
        "episode_name": "The Boy in the Iceberg"
      },
      {
        "episode_number": "02",
        "episode_name": "The Avatar Returns"
      }
    ],
    "request_date": "2024-03-14T09:21:00.000Z"
  }
]
```

### Example prompts

It's good to first instruct Claude to use Overseerr. Then it will always call the tool when appropriate.

Try prompts like these:
- Get the status of our Overseerr server
- Show me all the movie requests that are currently pending
- List all TV show requests from the last month that are now available
- What movies have been requested but are not available yet?
- What TV shows have recently become available in our library?

## Configuration

### Overseerr API Key & URL

There are two ways to configure the environment with the Overseerr API credentials:

1. Add to server config (preferred)

```json
{
  "overseerr-mcp": {
    "command": "uvx",
    "args": [
      "overseerr-mcp"
    ],
    "env": {
      "OVERSEERR_API_KEY": "<your_api_key_here>",
      "OVERSEERR_URL": "<your_overseerr_url>"
    }
  }
}
```

2. Create a `.env` file in the working directory with the following required variables:

```
OVERSEERR_API_KEY=your_api_key_here
OVERSEERR_URL=your_overseerr_url_here
```

Note: You can find the API key in the Overseerr settings under "API Keys".

## Quickstart

### Install

#### Overseerr API Key

You need an Overseerr instance running and an API key:
1. Navigate to your Overseerr installation
2. Go to Settings → General
3. Find the "API Key" section
4. Generate a new API key if you don't already have one

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "overseerr-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/overseerr-mcp",
        "run",
        "overseerr-mcp"
      ],
      "env": {
        "OVERSEERR_API_KEY": "<your_api_key_here>",
        "OVERSEERR_URL": "<your_overseerr_url>"
      }
    }
  }
}
```
</details>

**Note: This MCP server is not yet published. Currently, only the development configuration is available.**

### Run

Set the required environment variables before starting the server:

```bash
export OVERSEERR_API_KEY="<your_api_key_here>"
export OVERSEERR_URL="https://your-overseerr.example.com"
```

#### Published package

```bash
uvx overseerr-mcp
```

#### Run from this repository

```bash
uv run overseerr-mcp
```

You can also define the variables in a `.env` file in the project root if you prefer not to export them in your shell.

**Example invocation**

```bash
OVERSEERR_API_KEY=demo OVERSEERR_URL=https://overseerr.example.com uv run overseerr-mcp
```

You should see log lines similar to the following when the server has started successfully:

```text
[2025-10-24 07:58:52] INFO     Starting MCP server 'Overseerr Media Request Handler' with transport 'http' on http://0.0.0.0:8000/mcp
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
Server started successfully.
```

## Development

### Building

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

### Testing

Set up a uv-managed virtual environment and run the test suite with pytest:

```bash
uv venv
uv run python -m pytest
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/overseerr-mcp run overseerr-mcp
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-overseerr-mcp.log
```

## License

MIT
