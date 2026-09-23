def clip(text: str, limit: int = 3000) -> str:
    """Keep the tail of long output, where errors usually are."""
    return text if len(text) <= limit else "...(truncated)\n" + text[-limit:]