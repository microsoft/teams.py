"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from .agent import AGENT_PATH, build_app  # noqa: E402

PORT = 3979
BASE_URL = f"http://localhost:{PORT}"


if __name__ == "__main__":
    app = FastAPI()
    app.mount(AGENT_PATH, build_app(base_url=BASE_URL))
    uvicorn.run(app, host="127.0.0.1", port=PORT)
