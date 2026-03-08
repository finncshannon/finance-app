"""Custom exception types for data provider errors."""


class ProviderError(Exception):
    """Base exception for all provider errors."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class ProviderTimeout(ProviderError):
    """Raised when a provider request times out."""

    def __init__(self, provider: str, ticker: str, timeout_seconds: float):
        self.ticker = ticker
        self.timeout_seconds = timeout_seconds
        super().__init__(provider, f"Request for '{ticker}' timed out after {timeout_seconds}s")


class ProviderConnectionError(ProviderError):
    """Raised when a provider is unreachable."""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(provider, f"Connection failed{': ' + detail if detail else ''}")


class RateLimitError(ProviderError):
    """Raised when the provider rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f" — retry after {retry_after}s"
        super().__init__(provider, msg)


class DataNotFoundError(ProviderError):
    """Raised when no data is found for the given ticker."""

    def __init__(self, provider: str, ticker: str, data_type: str = "data"):
        self.ticker = ticker
        self.data_type = data_type
        super().__init__(provider, f"No {data_type} found for '{ticker}'")
