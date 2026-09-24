import asyncio
import python_weather
import inspect
import sys
from llama_index.core.tools import FunctionTool
from harness import run_process, read_file
from ddgs import DDGS

def list_tools() -> list[FunctionTool]:
    """
    Lists all available tools.

    Returns:
        list[FunctionTool]: A list of available tools.
    """
    return [
    FunctionTool.from_defaults(fn=tool["fn"], name=name, description=tool["description"])
    for name, tool in TOOLS_data.items()
    ]

async def search_web(query: str) -> str:
    """Searches the web for a query and returns the top results (title, URL, snippet)."""
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(DDGS().text, query, max_results=5),
            timeout=20,
        )
    except asyncio.TimeoutError:
        return "Search timed out after 20 seconds."
    except Exception as e:
        return f"Search failed: {type(e).__name__}: {e}"

    if not results:
        return "No results found."

    return "\n\n".join(
        f"{i}. {r['title']}\n   {r['href']}\n   {r['body']}"
        for i, r in enumerate(results, 1)
    )

async def get_weather(city: str) -> float:
    """
    Fetches the current temperature for a given city.
    """
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        weather = await asyncio.wait_for(client.get(city), timeout=20)
        return weather.temperature

async def run_code(code: str) -> str:
    """Executes the provided Python code and returns its exit code, stdout and stderr. Use print() to see values."""
    return await run_process([sys.executable, "-I", "-"], stdin=code)

async def run_bash(command: str) -> str:
    """Executes the provided bash command and returns its exit code, stdout and stderr."""
    return await run_process(["bash", "-c", command])

async def edit_file(file_path: str, old_str: str, new_str: str) -> str:
    """Replaces one exact occurrence of old_str with new_str in a file."""
    try:
        content = await asyncio.to_thread(read_file, file_path)
    except Exception as e:
        return f"Error opening file: {e}"

    count = content.count(old_str)
    if count == 0:
        return "Edit failed: old_str not found. Re-read the file and try again."
    if count > 1:
        return f"Edit failed: old_str matches {count} places. Include more surrounding context to make it unique."

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.replace(old_str, new_str, 1))
    return "Edit applied."

async def get_file_content(file_path: str) -> str:
    """Opens a file and returns its content."""
    return await asyncio.to_thread(read_file, file_path)

TOOLS_data = {
    "get_weather": {
        "description": "Fetches the current temperature for a given city, in Fahrenheit.",
        "args": {
            "city": {
                "type": "string",
                "description": "The name of the city to fetch the weather for."
            }
        },
        "fn": get_weather
    },

    "run_code": {
        "description": "Executes the provided code as a string and returns the stdout and stderr. Use print() to see values.",
        "args": {
            "code": {
                "type": "string",
                "description": "The code to execute."
            }
        },
        "fn": run_code
    },

    "run_bash": {
        "description": "Executes the provided bash command and returns the exit code, stdout and stderr.",
        "args": {
            "command": {
                "type": "string",
                "description": "The bash command to execute."
            }
        },
        "fn": run_bash
    },

    "get_file_content": {
        "description": "Opens a file and returns its content.",
        "args": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to open."
            }
        },
        "fn": get_file_content
    },

    "search_web": {
        "description": "Searches the web for a query and returns the top results (title, URL, snippet).",
        "args": {
            "query": {
                "type": "string",
                "description": "The search query."
            }
        },
        "fn": search_web
    },

    "edit_file": {
        "description": "Replaces one exact occurrence of old_str with new_str in a file",
        "args": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to edit."
            },
            "old_str": {
                "type": "string",
                "description": "The string to be replaced."
            },
            "new_str": {
                "type": "string",
                "description": "The string to replace with."
            }
        },
        "fn": edit_file
    }
}


async def execute_tool(tool_name: str, tool_args: dict):
    """
    Executes a specified tool with given arguments.

    Args:
        tool_name (str): The name of the tool to execute.
        tool_args (dict): A dictionary of arguments for the tool.

    Returns:
        Any: The result of the tool execution.
    """
    tool = TOOLS_data.get(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found.")

    fn = tool["fn"]
    return await fn(**tool_args) if inspect.iscoroutinefunction(fn) else fn(**tool_args)

    