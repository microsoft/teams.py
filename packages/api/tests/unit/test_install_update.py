"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from microsoft_teams.api.activities import ActivityTypeAdapter
from microsoft_teams.api.activities.install_update import InstalledUpgradeActivity


def test_installation_update_upgrade_parses() -> None:
    """Regression test for installationUpdate payloads that use action=upgrade."""
    payload = {
        "action": "upgrade",
        "channelId": "msteams",
        "conversation": {
            "conversationType": "personal",
            "id": "xxx",
            "tenantId": "xxx",
        },
        "entities": [
            {
                "locale": "en-US",
                "type": "clientInfo",
            }
        ],
        "from": {
            "aadObjectId": "xxx",
            "id": "xxx",
        },
        "id": "xxx",
        "recipient": {
            "id": "xxx",
            "name": "xxx",
        },
        "serviceUrl": "https://smba.trafficmanager.net/emea/xxx/",
        "timestamp": "2026-08-26T13:38:36.356Z",
        "type": "installationUpdate",
    }

    activity = ActivityTypeAdapter.validate_python(payload)

    assert isinstance(activity, InstalledUpgradeActivity)
    assert activity.action == "upgrade"
