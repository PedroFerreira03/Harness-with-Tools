import python_weather
import inspect
import ast
import contextlib
import io
import traceback
import linecache
from llama_index.core.tools import FunctionTool

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


async def get_weather(city: str) -> float:
    """
    Fetches the current temperature for a given city.

    Args:
        city (str): The name of the city.

    Returns:
        float: The current temperature in Fahrenheit.
    """
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        weather = await client.get(city)
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

    except Exception as e:
        if isinstance(e, SyntaxError):
            trace = "".join(traceback.format_exception_only(type(e), e))
        else:
            tb = e.__traceback__.tb_next or e.__traceback__
            trace = "".join(traceback.format_exception(type(e), e, tb))

        partial = buf.getvalue()
        msg = f"Execution failed:\n{trace}"
        if partial:
            msg = f"Output before the error:\n{partial}\n{msg}"
        return msg

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

    