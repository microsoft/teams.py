"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api import MessageActivityInput, PlanInfoEntity, Step, StepSource, StepStatus, TypingActivityInput
from pydantic import ValidationError


@pytest.mark.unit
class TestPlanInfoEntity:
    def test_serialization(self):
        entity = PlanInfoEntity(
            plan_type="continue",
            steps=[
                Step(
                    id="lookup",
                    version=2,
                    title="Sources checked",
                    status="completed",
                    description="Found the supporting report.",
                    sources=[StepSource(title="Report", url="https://example.com/report", icon="document")],
                )
            ],
        )

        assert entity.model_dump(by_alias=True, exclude_none=True) == {
            "type": "planInfo",
            "planType": "continue",
            "steps": [
                {
                    "id": "lookup",
                    "version": 2,
                    "title": "Sources checked",
                    "status": "completed",
                    "description": "Found the supporting report.",
                    "sources": [{"title": "Report", "url": "https://example.com/report", "icon": "document"}],
                }
            ],
        }

    def test_optional_fields_are_omitted_but_empty_lists_are_preserved(self):
        entity = PlanInfoEntity(plan_type="stop")
        assert entity.model_dump(exclude_none=True) == {"type": "planInfo", "planType": "stop"}
        entity.steps = []
        assert entity.model_dump(exclude_none=True)["steps"] == []

        step = Step(id="lookup", version=1, title="Lookup", status="active")
        assert step.model_dump(exclude_none=True) == {
            "id": "lookup",
            "version": 1,
            "title": "Lookup",
            "status": "active",
        }
        step.sources = []
        assert step.model_dump(exclude_none=True)["sources"] == []
        assert StepSource(title="Report", url="https://example.com").model_dump(exclude_none=True) == {
            "title": "Report",
            "url": "https://example.com",
        }

    @pytest.mark.parametrize("status", ["active", "proposed", "completed", "blocked", "error"])
    def test_step_status_serialization(self, status: StepStatus):
        step = Step(id="lookup", version=1, title="Lookup", status=status)
        assert step.model_dump()["status"] == status

    @pytest.mark.parametrize("activity_type", [TypingActivityInput, MessageActivityInput])
    @pytest.mark.parametrize("plan_type_key", ["plan_type", "planType"])
    def test_activity_parses_typed_plan_entity_and_serializes_aliases(self, activity_type, plan_type_key):
        data = {"entities": [{"type": "planInfo", plan_type_key: "continue", "steps": []}]}
        activity = activity_type.model_validate(data)

        assert isinstance(activity.entities[0], PlanInfoEntity)
        assert activity.model_dump(by_alias=True, exclude_none=True)["entities"] == [
            {"type": "planInfo", "planType": "continue", "steps": []}
        ]
        assert activity_type.model_validate_json(activity.model_dump_json(exclude_none=True)) == activity

    def test_invalid_plan_type_does_not_fall_back_to_unknown_entity(self):
        with pytest.raises(ValidationError, match="planType"):
            TypingActivityInput.model_validate({"entities": [{"type": "planInfo", "planType": "unknown"}]})

    def test_invalid_step_status(self):
        with pytest.raises(ValidationError, match="status"):
            Step.model_validate({"id": "lookup", "version": 1, "title": "Lookup", "status": "unknown"})
