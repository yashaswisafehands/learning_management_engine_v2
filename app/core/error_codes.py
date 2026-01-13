from enum import Enum


class ErrorCode(str, Enum):
    SAMPLE_NOT_FOUND = "SAMPLE_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    NOT_FOUND = "NOT_FOUND"


ERRORS = {
    ErrorCode.SAMPLE_NOT_FOUND: {
        "code": ErrorCode.SAMPLE_NOT_FOUND,
        "message": "The requested sample does not exist.",
        "status_code": 404,
    },
    ErrorCode.DATABASE_ERROR: {
        "code": ErrorCode.DATABASE_ERROR,
        "message": "Database operation failed.",
        "status_code": 500,
    },
    ErrorCode.INVALID_INPUT: {
        "code": ErrorCode.INVALID_INPUT,
        "message": "Input provided is not valid.",
        "status_code": 422,
    },
    ErrorCode.UNAUTHORIZED: {
        "code": ErrorCode.UNAUTHORIZED,
        "message": "User is not authorized to perform this action.",
        "status_code": 401,
    },
    ErrorCode.UNKNOWN_ERROR: {
        "code": ErrorCode.UNKNOWN_ERROR,
        "message": "An unknown error occurred.",
        "status_code": 500,
    },
    ErrorCode.NOT_FOUND: {
        "code": ErrorCode.NOT_FOUND,
        "message": "The requested resource was not found.",
        "status_code": 404,
    },
}
