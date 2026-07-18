"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

TEAMS_API_TRACER_NAME = "Microsoft.Teams.Api"
TEAMS_API_METER_NAME = "Microsoft.Teams.Api"


class TeamsApiTelemetry:
    """OpenTelemetry source names for the Teams API package."""

    tracer_name = TEAMS_API_TRACER_NAME
    meter_name = TEAMS_API_METER_NAME
