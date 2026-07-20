"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata

TEAMS_API_TRACER_NAME = "Microsoft.Teams.Api"
TEAMS_API_METER_NAME = "Microsoft.Teams.Api"
TEAMS_API_INSTRUMENTATION_VERSION = importlib.metadata.version("microsoft-teams-api")


class TeamsApiTelemetry:
    """OpenTelemetry source names for the Teams API package."""

    tracer_name = TEAMS_API_TRACER_NAME
    meter_name = TEAMS_API_METER_NAME
    instrumentation_version = TEAMS_API_INSTRUMENTATION_VERSION
