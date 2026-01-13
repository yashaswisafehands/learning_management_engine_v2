import uuid


def get_uid() -> str:
    return str(uuid.uuid4())
