import python_weather
import inspect
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

def add(x: float, y: float) -> float:
    """
    Adds two numbers.

    Args:
        x (float): The first number.
        y (float): The second number.

    Returns:
        float: The sum of x and y.
    """
    return x + y


TOOLS_data = {
    "get_weather": {
        "description": "Fetches the current temperature for a given city.",
        "args": {
            "city": {
                "type": "string",
                "description": "The name of the city to fetch the weather for."
            }
        },
        "fn": get_weather
    },

    "add": {
        "description": "Adds two numbers.",
        "args": {
            "x": {
                "type": "number",
                "description": "The first number."
            },
            "y": {
                "type": "number",
                "description": "The second number."
            }
        },
        "fn": add
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

    