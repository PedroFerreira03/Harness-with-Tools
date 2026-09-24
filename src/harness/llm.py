from llama_index.llms.ollama import Ollama

def initialize_model() -> Ollama:
    """
    Initializes the Ollama model.

    Returns:
        Ollama: An instance of the Ollama model.
    """
    return Ollama(model="qwen3:8b",
                context_window=8000,
                request_timeout=300)