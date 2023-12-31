class InvalidAPIKeyError(Exception):
    """Exception raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key"):
        self.message = message
        super().__init__(self.message)


class APISyntaxError(Exception):
    """Exception raised when the API syntax is incorrect."""

    def __init__(self, message: str = "Invalid API syntax"):
        self.message = message
        super().__init__(self.message)
