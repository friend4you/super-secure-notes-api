from fastapi import HTTPException


class APIError(HTTPException):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"error": error, "message": message})
        self.error = error
        self.message = message
