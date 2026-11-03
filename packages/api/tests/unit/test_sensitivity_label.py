"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any

import pytest
from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.models.entity import (
    CitationAppearance,
    CitationUsageInfo,
    SensitivityUsageInfo,
)
from pydantic import ValidationError


def _entities(activity: MessageActivityInput) -> list[dict[str, Any]]:
    return activity.model_dump(by_alias=True, exclude_none=True)["entities"]


def _root_entities(activity: MessageActivityInput) -> list[dict[str, Any]]:
    return [
        e for e in _entities(activity) if e.get("type") == "https://schema.org/Message" and e.get("@type") == "Message"
    ]


class TestCitationUsageInfo:
    def test_id_only_serializes_without_root_entity_fields(self) -> None:
        activity = MessageActivityInput(text="hi").add_citation(
            1,
            CitationAppearance(name="doc", abstract="abstract", usage_info=SensitivityUsageInfo(at_id="label-id")),
        )

        usage_info = _root_entities(activity)[0]["citation"][0]["appearance"]["usageInfo"]
        assert usage_info == {"@type": "CreativeWork", "@id": "label-id"}

    def test_passes_through_custom_type(self) -> None:
        activity = MessageActivityInput(text="hi").add_citation(
            1,
            CitationAppearance(
                name="doc", abstract="abstract", usage_info=SensitivityUsageInfo(at_type="CustomType", at_id="label-id")
            ),
        )

        usage_info = _root_entities(activity)[0]["citation"][0]["appearance"]["usageInfo"]
        assert usage_info == {"@type": "CustomType", "@id": "label-id"}

    def test_copies_usage_info(self) -> None:
        usage_info = SensitivityUsageInfo(at_id="label-id", name="Confidential")
        activity = MessageActivityInput(text="hi").add_citation(
            1, CitationAppearance(name="doc", abstract="abstract", usage_info=usage_info)
        )

        usage_info.name = "Changed"

        assert _root_entities(activity)[0]["citation"][0]["appearance"]["usageInfo"]["name"] == "Confidential"

    def test_deprecated_alias_still_accepted(self) -> None:
        with pytest.deprecated_call():
            usage_info = CitationUsageInfo(at_id="label-id", name="Confidential", description="Internal only")

        activity = MessageActivityInput(text="hi").add_citation(
            1, CitationAppearance(name="doc", abstract="abstract", usage_info=usage_info)
        )

        assert _root_entities(activity)[0]["citation"][0]["appearance"]["usageInfo"] == {
            "@type": "CreativeWork",
            "@id": "label-id",
            "name": "Confidential",
            "description": "Internal only",
        }

    def test_deprecated_alias_requires_name_and_description(self) -> None:
        with pytest.deprecated_call(), pytest.raises(ValidationError):
            CitationUsageInfo(at_id="label-id")


class TestInboundUsageInfoWithoutId:
    def _parse(self, root_fields: dict[str, Any]) -> list[dict[str, Any]]:
        payload = {
            "type": "message",
            "text": "hi",
            "entities": [
                {
                    "type": "https://schema.org/Message",
                    "@type": "Message",
                    "@context": "https://schema.org",
                    **root_fields,
                }
            ],
        }
        return _entities(MessageActivityInput.model_validate(payload))

    def test_message_label_parses(self) -> None:
        entities = self._parse({"usageInfo": {"@type": "CreativeWork", "name": "Confidential"}})

        assert entities[0]["usageInfo"] == {"@type": "CreativeWork", "name": "Confidential"}

    def test_citation_label_parses(self) -> None:
        appearance = {
            "@type": "DigitalDocument",
            "name": "doc",
            "abstract": "abstract",
            "usageInfo": {"@type": "CreativeWork", "name": "Confidential"},
        }
        entities = self._parse({"citation": [{"@type": "Claim", "position": 1, "appearance": appearance}]})

        assert entities[0]["citation"][0]["appearance"]["usageInfo"] == {
            "@type": "CreativeWork",
            "name": "Confidential",
        }
