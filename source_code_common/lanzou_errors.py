from enum import Enum


class ErrorCode(str, Enum):
    INVALID_LINK = "invalid_link"
    LIST_API_UNAVAILABLE = "list_api_unavailable"
    PASSWORD_REQUIRED = "password_required"
    PASSWORD_INCORRECT = "password_incorrect"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    NETWORK = "network"
    PARSE = "parse"
    UNKNOWN = "unknown"


class LanzouError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
