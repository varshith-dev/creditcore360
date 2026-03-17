class OllamaUnavailableError(Exception):
    """Raised when Ollama endpoint is unreachable"""
    pass


class OllamaTimeoutError(Exception):
    """Raised when Ollama request times out"""
    pass


class OllamaModelError(Exception):
    """Raised when Ollama model returns an error"""
    pass


class JSONExtractionError(Exception):
    """Raised when JSON extraction fails from Ollama response"""
    pass
