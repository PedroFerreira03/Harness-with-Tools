import asyncio
import python_weather
import inspect
import ast
import contextlib
import io
import traceback
import linecache
from llama_index.core.tools import FunctionTool
from harness import clip
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

    Args:
        city (str): The name of the city.

    Returns:
        float: The current temperature in Fahrenheit.
    """
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        weather = await asyncio.wait_for(client.get(city), timeout=20)
        return weather.temperature


def run_code(code: str) -> str:
    """Executes the provided code and returns the result."""
    buf = io.StringIO()
    linecache.cache["<llm>"] = (len(code), None, code.splitlines(True), "<llm>")

    try:
        tree = ast.parse(code)
        last_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = ast.Expression(tree.body.pop().value)

        env = {}
        with contextlib.redirect_stdout(buf):
            exec(compile(tree, "<llm>", "exec"), env)
            result = eval(compile(last_expr, "<llm>", "eval"), env) if last_expr else None

        output = buf.getvalue()
        if result is not None:
            output += repr(result)
        return output or "(no output)"

    except Exception:
        trace = traceback.format_exc()
        trace = clip(trace)
        partial = buf.getvalue()
        msg = f"Execution failed:\n{trace}"
        if partial:
            msg = f"Output before the error:\n{partial}\n{msg}"
        return msg

async def run_bash(command: str) -> str:
    """Executes the provided bash command and returns its exit code, stdout and stderr."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        return f"Could not start the command: {e}"

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "Command timed out after 60 seconds."

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    parts = [f"Exit code: {proc.returncode}"]
    if out:
        parts.append(f"stdout:\n{clip(out)}")
    if err:
        parts.append(f"stderr:\n{clip(err)}")
    if not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)

def get_file_content(file_path: str) -> str:
    """Opens a file and returns its content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error opening file: {e}"

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
        "description": "Executes the provided code as a string and returns the result.",
        "args": {
            "code": {
                "type": "string",
                "description": "The code to execute."
            }
        },
        "fn": run_code
    },

    "run_bash": {
        "description": "Executes the provided bash command and returns the result.",
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

    