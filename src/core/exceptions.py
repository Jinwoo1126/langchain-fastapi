from fastapi import HTTPException
from starlette import status

class LLMServiceError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

class InvalidRequestError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
