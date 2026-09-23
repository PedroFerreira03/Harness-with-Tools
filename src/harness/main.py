import asyncio
from llama_index.core.llms import ChatMessage, MessageRole
from harness.tools import list_tools, execute_tool
from harness.llm import initialize_model


async def main():
    while True:
        llm = initialize_model()
        tools = list_tools()

        system_message = """You are a helpful assistant that can use tools to answer questions. 
        You have access to tools. After every tool result, you should think about its result and plan the steps ahead before continuing on."""

        query = str(input("\n> Enter your query (or 'exit' to quit): "))
        if query.lower() == "exit":
            break

        chat_history = [ChatMessage(role='system', content=system_message), ChatMessage(role="user", content=query)]

        while True:
            print("\n[Assistant]")
            response_gen = await llm.astream_chat_with_tools(tools, chat_history=chat_history)

            last_chunk = None
            async for chunk in response_gen:
                if chunk.delta:
                    print(chunk.delta, end="", flush=True)
                last_chunk = chunk
            print() 

            tool_calls = llm.get_tool_calls_from_response(last_chunk, error_on_no_tool_call=False)
            chat_history.append(last_chunk.message)

            if not tool_calls:
                decision = str(input("\n[System] What do you want to do? (new, continue, exit) "))
                match decision.lower():
                    case "exit":
                        return
                    case "new":
                        break
                    case "continue":
                        new_query = str(input("\n> Enter your new query: "))
                        chat_history.append(ChatMessage(role="user", content=new_query))
                        continue

            for tc in tool_calls:
                print(f"[Tool Call] {tc.tool_name}({tc.tool_kwargs})")

            results = await asyncio.gather(
                *(execute_tool(tool_name=tc.tool_name, tool_args=tc.tool_kwargs) for tc in tool_calls)
            )


            print("")
            for tool_call, result in zip(tool_calls, results):
                print(f"[Tool Result] {tool_call.tool_name} -> {result}")
                chat_history.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content=str(result),
                        additional_kwargs={"tool_call_id": tool_call.tool_id},
                    )
                )

if __name__ == "__main__":
    asyncio.run(main())
    