"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os

from dotenv import find_dotenv, load_dotenv

# Constants for app types
SINGLE_TENANT = "singletenant"
MULTI_TENANT = "multitenant"


class DefaultConfig:
    """Bot Configuration"""

    def __init__(self):
        load_dotenv(find_dotenv(usecwd=True))
        self.PORT = os.getenv("PORT", "")
        self.APP_ID = os.getenv("CLIENT_ID", "")
        self.APP_PASSWORD = os.getenv("CLIENT_SECRET", "")
        self.APP_TENANTID = os.getenv("TENANT_ID", "")
        self.APP_TYPE = SINGLE_TENANT if self.APP_TENANTID else MULTI_TENANT
