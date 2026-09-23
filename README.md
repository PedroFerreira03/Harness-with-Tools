# MCP Implementation: a local tool-calling agent harness

A small command-line agent that runs a local LLM through **Ollama** and lets it call tools to answer questions: check the weather, search the web, run Python, run shell commands, and read files. The model streams its reply, decides which tools to call, sees the results, and keeps going until it has an answer.

Built with [LlamaIndex](https://www.llamaindex.ai/) for the model client and tool schemas, and plain `asyncio` for running tools in parallel.

## How it works

```
 you ──► main.py ──► LLM (Ollama, qwen3:8b)
            ▲              │
            │              ▼ tool calls
            └──── tools.py (execute_tool) ◄── get_weather, run_code, run_bash, ...
                     tool results fed back into the chat history
```

1. You type a query.
2. The model streams its answer. If it requests tool calls, they are printed as `[Tool Call]` and executed concurrently with `asyncio.gather`.
3. Results are appended to the chat history as tool messages (`[Tool Result]`), and the model is called again.
4. When the model answers without calling a tool, you choose `new`, `continue`, or `exit`.

The system prompt tells the model to think about each tool result and plan its next steps before continuing.

## Project layout

```
src/harness/
├── main.py    # interactive loop: streaming, tool-call dispatch, chat history
├── llm.py     # initialize_model(): creates the Ollama client
├── tools.py   # tool functions, TOOLS_data registry, list_tools(), execute_tool()
```

`tools.py` imports a `clip` helper from the `harness` package. It truncates long output, keeping the tail where errors usually are.

## Tools

| Tool | What it does |
|---|---|
| `get_weather(city)` | Current temperature in Fahrenheit (via `python_weather`, 20 s timeout). |
| `search_web(query)` | Top 5 DuckDuckGo results as title, URL, snippet (via `ddgs`, 20 s timeout). |
| `run_code(code)` | Runs Python in-process. Prints are captured, and the value of a trailing expression is returned, like a REPL. Errors return a full traceback plus any output printed before the failure. |
| `run_bash(command)` | Runs `bash -c <command>` with a 60 s timeout. Returns the exit code, stdout, and stderr. |
| `get_file_content(file_path)` | Reads a UTF-8 text file and returns its contents. |

Errors inside most tools are returned as text instead of raised, so the model can read them and retry.

### Adding a tool

1. Write a function with type hints (sync or `async`) that returns a string.
2. Add an entry to `TOOLS_data` in `tools.py` with a `description` and the `fn`.

`list_tools()` builds each `FunctionTool` from the function's signature and type hints plus the entry's `name` and `description`. The `args` dictionaries in `TOOLS_data` are documentation only and are not read by `list_tools()`. `execute_tool()` awaits coroutine functions and calls sync ones directly.

## Requirements & How to Run

- Python 3.12
- [Ollama](https://ollama.com/) installed and running, with the model pulled
- `bash` on your PATH for `run_bash`: WSL or Git Bash on Windows

```bash
uv sync
ollama pull qwen3:8b
uv run python ./src/main.py
```

This will this appears on the terminal:
```
> Enter your query (or 'exit' to quit): what's the average of 1, 3, 2, 1, 1, 45, 122, 3?

[Assistant]
[Tool Call] run_code({'code': '...'})
[Tool Result] run_code -> 22.125
```

## Safety notes

This gives an LLM real capabilities on your machine. Treat it as a local experiment.

- **`run_code` and `run_bash` are not sandboxed.** The model can read, modify, or delete anything your user account can. Run the harness in a container or VM, or add a `y/n` confirmation before executing them.
- **`get_file_content` has no path restrictions or size limit.** It can read any file you can, and a large file can fill the context window.
- **Prompt injection.** Web results are untrusted text, and a malicious page could try to instruct the model. Having `search_web` alongside `run_bash` and `run_code` makes this matter, so confirm dangerous commands by hand.
- `run_code` cannot be interrupted if the code loops forever, since it runs in-process with no timeout. `run_bash` has a 60 s timeout.

## Known limitations

- **Unhandled tool exceptions crash the loop.** Tools like `get_weather` can still raise (for example on a timeout), and `execute_tool` doesn't catch it. Wrapping the call in `try/except` and returning the error as text would fix it.
- **Invalid input at the decision prompt** (anything other than `new`, `continue`, `exit`) falls through and calls the model again.
- **`chat_history` grows without bound** during a session and counts against the context window. Long tool loops can eventually exceed it.
- **Despite the project name, tools currently run in-process.** They aren't exposed over MCP yet. Moving them to an MCP server is a possible next step: each function becomes an `@mcp.tool()`, and `tools.py` becomes a client.

## Switching to vLLM

`main.py` only calls `initialize_model()`, so the backend can be swapped by changing `llm.py` alone. vLLM exposes an OpenAI-compatible server, which LlamaIndex reaches through `OpenAILike` (`pip install llama-index-llms-openai-like`) with `is_chat_model=True` and `is_function_calling_model=True`. The server must be started with `--enable-auto-tool-choice --tool-call-parser hermes`. vLLM doesn't officially support native Windows, so use WSL2 there.