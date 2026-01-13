from fastapi import HTTPException

from app.core.error_codes import ERRORS, ErrorCode


class AppException(HTTPException):
    def __init__(self, error_code: ErrorCode, detail: str | None = None):
        error = ERRORS[error_code]
        super().__init__(
            status_code=error["status_code"],
            detail={
                "code": error["code"],
                "message": detail or error["message"],
            },
        )


class GraphNotFoundException(AppException):
    def __init__(self, detail: str = "Requested resource not found"):
        super().__init__(ErrorCode.NOT_FOUND, detail)


class GraphConflictException(AppException):
    def __init__(self, detail: str = "Conflict occurred (e.g., duplicate key)"):
        super().__init__(ErrorCode.INVALID_INPUT, detail)


class GraphDatabaseException(AppException):
    def __init__(self, detail: str = "Graph database operation failed"):
        super().__init__(ErrorCode.DATABASE_ERROR, detail)


class GraphOperationException(AppException):
    def __init__(self, detail: str = "Graph operation failed"):
        super().__init__(ErrorCode.UNKNOWN_ERROR, detail)
