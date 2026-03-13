from collections.abc import Generator


def get_db() -> Generator[None, None, None]:
    yield None
