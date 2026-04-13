"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import pytest
from microsoft_teams.api.models.entity import (
    Appearance,
    CitationAppearance,
    CitationIconName,
)


@pytest.mark.unit
class TestCitationAppearanceValidation:
    def _valid_kwargs(self) -> dict:
        return {"name": "My Document", "abstract": "A short abstract"}

    def test_name_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Name must be at most 80 characters long"):
            CitationAppearance(name="x" * 81, abstract="valid abstract")

    def test_abstract_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Abstract must be at most 160 characters long"):
            CitationAppearance(name="Valid Name", abstract="x" * 161)

    def test_too_many_keywords_raises(self) -> None:
        with pytest.raises(ValueError):
            CitationAppearance(name="Doc", abstract="Abstract", keywords=["a", "b", "c", "d"])

    def test_keyword_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Each keyword must be at most 28 characters long"):
            CitationAppearance(name="Doc", abstract="Abstract", keywords=["k" * 29])

    def test_valid_citation_appearance(self) -> None:
        ca = CitationAppearance(
            name="Valid Document",
            abstract="This is a valid abstract.",
            keywords=["python", "teams"],
            icon=CitationIconName.PDF,
        )
        assert ca.name == "Valid Document"
        assert ca.keywords == ["python", "teams"]


@pytest.mark.unit
class TestAppearanceValidation:
    def test_name_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Name must be at most 80 characters long"):
            Appearance(name="x" * 81, abstract="valid abstract")

    def test_abstract_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Abstract must be at most 160 characters long"):
            Appearance(name="Valid Name", abstract="x" * 161)

    def test_too_many_keywords_raises(self) -> None:
        with pytest.raises(ValueError):
            Appearance(name="Doc", abstract="Abstract", keywords=["a", "b", "c", "d"])

    def test_keyword_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="Each keyword must be at most 28 characters long"):
            Appearance(name="Doc", abstract="Abstract", keywords=["k" * 29])

    def test_valid_appearance(self) -> None:
        ap = Appearance(
            name="Valid Document",
            abstract="This is a valid abstract.",
            keywords=["search", "ai"],
        )
        assert ap.name == "Valid Document"
        assert ap.at_type == "DigitalDocument"
