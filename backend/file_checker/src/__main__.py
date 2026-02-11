import os

import uvicorn

from src import app_object


def main() -> None:
    host = os.getenv("FILE_CORE_HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("FILE_CORE_HTTP_PORT", "8003"))
    uvicorn.run(app_object, host=host, port=port)


if __name__ == "__main__":
    main()

