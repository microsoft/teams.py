"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import uvicorn
from fastapi import FastAPI

from .agent import AGENT_PATH, build_app

PORT = 3979
BASE_URL = f"http://localhost:{PORT}"


if __name__ == "__main__":
    app = FastAPI()
    app.mount(AGENT_PATH, build_app(base_url=BASE_URL))
    uvicorn.run(app, host="127.0.0.1", port=PORT)
