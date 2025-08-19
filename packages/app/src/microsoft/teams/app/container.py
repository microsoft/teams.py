"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
