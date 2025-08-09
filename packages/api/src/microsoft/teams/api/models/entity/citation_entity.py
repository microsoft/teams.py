"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Literal, Optional

from pydantic import field_validator

from ..custom_base_model import CustomBaseModel
from .message_entity import MessageEntity

# Citation icon names for different file types and applications.
CitationIconName = (
    Literal[
        "Microsoft Word",
        "Microsoft Excel",
        "Microsoft PowerPoint",
        "Microsoft OneNote",
        "Microsoft SharePoint",
        "Microsoft Visio",
        "Microsoft Loop",
        "Microsoft Whiteboard",
        "Adobe Illustrator",
        "Adobe Photoshop",
        "Adobe InDesign",
        "Adobe Flash",
        "Sketch",
        "Source Code",
        "Image",
        "GIF",
        "Video",
        "Sound",
        "ZIP",
        "Text",
        "PDF",
    ]
    | str
)


class CitationUsageInfo(CustomBaseModel):
    """Sensitivity content information"""

    at_id: str
    "Unique identifier for the usage info"

    description: str
    "Description of the usage info"

    name: str
    "Name of the usage info"

    position: Optional[int] = None
    "Position of the usage info"


class Image(CustomBaseModel):
    """Information about the citation's icon"""

    at_type: Literal["ImageObject"] = "ImageObject"
    "Type for the image"

    name: CitationIconName
    "The image/icon name"


class CitationAppearance(CustomBaseModel):
    @field_validator("name")
    @classmethod
    def check_name(cls, value: Any) -> Any:
        if len(value) > 80:
            raise ValueError("Name must be at most 80 characters long")
        return value

    @field_validator("abstract")
    @classmethod
    def check_abstract(cls, value: Any) -> Any:
        if len(value) > 160:
            raise ValueError("Abstract must be at most 160 characters long")
        return value

    @field_validator("keywords")
    @classmethod
    def check_keywords(cls, value: Any) -> Any:
        if value is not None:
            if len(value) > 3:
                raise ValueError("Each keyword must be at most 28 characters long")
            if any(len(keyword) > 28 for keyword in value):
                raise ValueError("Each keyword must be at most 28 characters long")
        return value

    name: str
    "Name of the document (max length 80)"

    text: Optional[str] = None
    "Stringified adaptive card with additional information about the citation. It is rendered within a modal"

    url: Optional[str] = None
    "URL of the document. This will make the name of the citation clickable and direct the user to the specified URL"

    abstract: str
    "Extract of the referenced content (max length 160)"

    icon: Optional[CitationIconName] = None
    "Information about the citation's icon"

    keywords: Optional[List[str]] = None
    "Keywords (max length 3) (max keyword length 28)"

    usage_info: Optional[CitationUsageInfo] = None
    "Sensitivity content information"


class Appearance(CustomBaseModel):
    """Appearance options for a citation"""

    @field_validator("name")
    @classmethod
    def check_name(cls, value: Any) -> Any:
        if len(value) > 80:
            raise ValueError("Name must be at most 80 characters long")
        return value

    @field_validator("abstract")
    @classmethod
    def check_abstract(cls, value: Any) -> Any:
        if len(value) > 160:
            raise ValueError("Abstract must be at most 160 characters long")
        return value

    @field_validator("keywords")
    @classmethod
    def check_keywords(cls, value: Any) -> Any:
        if value is not None:
            if len(value) > 3:
                raise ValueError("Each keyword must be at most 28 characters long")
            if any(len(keyword) > 28 for keyword in value):
                raise ValueError("Each keyword must be at most 28 characters long")
        return value

    at_type: Literal["DigitalDocument"] = "DigitalDocument"
    "Must be 'DigitalDocument'"

    name: str
    "Name of the document (max length 80)"

    text: Optional[str] = None
    "Stringified adaptive card with additional information about the citation. It is rendered within a modal"

    url: Optional[str] = None
    "URL of the document. This will make the name of the citation clickable and direct the user to the specified URL"

    abstract: str
    "Extract of the referenced content (max length 160)"

    encoding_format: Optional[Literal["application/vnd.microsoft.card.adaptive"]] = (
        "application/vnd.microsoft.card.adaptive"
    )
    "Encoding format of the `text`"

    image: Optional[Image] = None
    "Citation image information"

    keywords: Optional[List[str]] = None
    "Keywords (max length 3) (max keyword length 28)"

    usage_info: Optional[CitationUsageInfo] = None
    "Sensitivity content information"


class Claim(CustomBaseModel):
    at_type: Literal["Claim"] = "Claim"
    "Required as 'Claim'"

    position: int
    "Position of the citation"

    appearance: Appearance
    "Appearance options"


class CitationEntity(MessageEntity):
    citation: Optional[List[Claim]] = None
    "Required as 'Citation'"
