from llama_index.llms.ollama import Ollama

def initialize_model() -> Ollama:
    """
    Initializes the Ollama model.

    Returns:
        Ollama: An instance of the Ollama model.
    """
    return Ollama(model="gemma4:12b")