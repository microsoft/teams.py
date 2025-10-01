"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, NotRequired, Union

from typing_extensions import TypedDict

ActionType = Literal["executeFunction", "openPage"]
Align = Literal["after", "before"]
AuthType = Literal["none", "apiSecretServiceAuth", "microsoftEntra"]
CommandContext = Literal["compose", "commandBox", "message"]
CommandListScope = Literal["team", "personal", "groupChat"]
CommandType = Literal["query", "action"]
ComposeExtensionType = Literal["botBased", "apiBased"]
ConfigurableProperty = Literal[
    "name",
    "shortDescription",
    "longDescription",
    "smallImageUrl",
    "largeImageUrl",
    "accentColor",
    "developerUrl",
    "privacyUrl",
    "termsOfUseUrl",
]
ConfigurableTabContext = Literal[
    "personalTab",
    "channelTab",
    "privateChatTab",
    "meetingChatTab",
    "meetingDetailsTab",
    "meetingSidePanel",
    "meetingStage",
]
ConfigurableTabScope = Literal["team", "groupChat"]
ConnectorScope = Literal["team"]
DefaultInstallScope = Literal["personal", "team", "groupChat", "meetings"]
DefaultSize = Literal["medium", "large"]
DevicePermission = Literal["geolocation", "media", "notifications", "midi", "openExternal"]
ExtensionContext = Literal[
    "mailRead",
    "mailCompose",
    "meetingDetailsOrganizer",
    "meetingDetailsAttendee",
    "onlineMeetingDetailsOrganizer",
    "logEventMeetingDetailsAttendee",
    "default",
]
FormFactor = Literal["desktop", "mobile"]
FluffyType = Literal["button", "menu"]

Groupchat = Literal["tab", "bot", "connector"]
InputType = Literal["text", "textarea", "number", "date", "time", "toggle", "choiceset"]
ItemType = Literal["menuItem"]
Lifetime = Literal["short", "long"]
ManifestVersion = Literal["1.19"]
MeetingSurface = Literal["sidePanel", "stage"]
MessageHandlerType = Literal["link"]
Permission = Literal["identity", "messageTeamMembers"]
PurpleType = Literal["mobileButton"]
RequirementsScope = Literal["mail", "workbook", "document", "presentation"]
ResourceSpecificType = Literal["Application", "Delegated"]
RuntimeType = Literal["general"]
SendMode = Literal["promptUser", "softBlock", "block"]
SourceType = Literal["bot"]
SupportedChannelType = Literal["sharedChannels", "privateChannels"]
SupportedSharePointHost = Literal["sharePointFullPage", "sharePointWebPart"]
StaticTabContext = Literal[
    "personalTab",
    "channelTab",
    "privateChatTab",
    "meetingChatTab",
    "meetingDetailsTab",
    "meetingSidePanel",
    "meetingStage",
    "teamLevelApp",
]


class Description(TypedDict):
    full: str
    """The full description of the app. Maximum length is 4000 characters."""
    short: str
    """A short description of the app used when space is limited. Maximum length is 80 characters."""


class Icons(TypedDict):
    color: str
    """A relative file path to a full color PNG icon. Size 192x192."""
    outline: str
    """A relative file path to a transparent PNG outline icon. The border color needs to be white. Size 32x32."""


class ActivityType(TypedDict):
    description: str
    templateText: str
    type: str


class Activities(TypedDict):
    """Specify the types of activites that your app can post to a users activity feed"""

    activityTypes: NotRequired[List[ActivityType]]


class AdditionalLanguage(TypedDict):
    file: str
    """A relative file path to a the .json file containing the translated strings."""
    languageTag: str
    """The language tag of the strings in the provided file."""


class APISecretServiceAuthConfiguration(TypedDict):
    """Object capturing details needed to do service auth. It will be only present when
    auth type is apiSecretServiceAuth."""

    apiSecretRegistrationId: NotRequired[str]
    """Registration id returned when developer submits the api key through Developer Portal."""


class ExtensionCommonIcon(TypedDict):
    size: int
    """Size in pixels of the icon. Three image sizes are required (16, 32, and 80 pixels)"""
    url: str
    """Absolute Url to the icon."""


class AlternateIcons(TypedDict):
    highResolutionIcon: ExtensionCommonIcon
    icon: ExtensionCommonIcon


class CommandListCommand(TypedDict):
    description: str
    """A simple text description or an example of the command syntax and its arguments."""
    title: str
    """The bot command name"""


class CommandList(TypedDict):
    commands: List[CommandListCommand]
    """An array of commands that power the Copilot experience by enabling rich interactions
    and functionalities supported by the bot."""
    scopes: List[CommandListScope]
    """Specifies the scopes for which the command list is valid"""


class TaskInfo(TypedDict):
    height: NotRequired[str]
    """Dialog height - either a number in pixels or default layout such as 'large', 'medium', or 'small'"""
    title: str
    """Initial dialog title"""
    url: NotRequired[str]
    """Initial webview URL"""
    width: NotRequired[str]
    """Dialog width - either a number in pixels or default layout such as 'large', 'medium', or 'small'"""


class GroupChat(TypedDict):
    fetchTask: bool
    """Indicates if it should fetch dialog dynamically."""
    taskInfo: TaskInfo
    """Dialog to be launched when fetch task set to false."""


class Configuration(TypedDict):
    groupChat: NotRequired[GroupChat]
    team: NotRequired[GroupChat]


class Bot(TypedDict):
    botId: str
    """The Microsoft App ID specified for the bot in the Bot Framework portal (https://dev.botframework.com/bots)"""
    commandLists: NotRequired[List[CommandList]]
    """The list of commands that the bot supplies, including their usage, description, and the scope for which
    the commands are valid. A separate command list should be used for each scope."""
    configuration: NotRequired[Configuration]
    isNotificationOnly: NotRequired[bool]
    """A value indicating whether or not the bot is a one-way notification only bot, as opposed to
    a conversational bot."""
    needsChannelSelector: NotRequired[bool]
    """This value describes whether or not the bot utilizes a user hint to add the bot to a specific channel."""
    scopes: List[CommandListScope]
    """Specifies whether the bot offers an experience in the context of a channel in a team, in a 1:1 or group chat, or
    in an experience scoped to an individual user alone. These options are non-exclusive."""
    supportsCalling: NotRequired[bool]
    """A value indicating whether the bot supports audio calling."""
    supportsFiles: NotRequired[bool]
    """A value indicating whether the bot supports uploading/downloading of files."""
    supportsVideo: NotRequired[bool]
    """A value indicating whether the bot supports video calling."""


class BotConfiguration(TypedDict):
    """The configuration for the bot source. Required if sourceType is set to bot."""

    botId: NotRequired[str]
    """The unique Microsoft app ID for the bot as registered with the Bot Framework."""


class COMAddin(TypedDict):
    progId: str
    """Program ID of the alternate com extension. Maximum length is 64 characters."""


class ConfigurableTab(TypedDict):
    canUpdateConfiguration: NotRequired[bool]
    """A value indicating whether an instance of the tab's configuration can be updated by the user after creation."""
    configurationUrl: str
    """The url to use when configuring the tab."""
    context: NotRequired[List[ConfigurableTabContext]]
    """The set of contextItem scopes that a tab belong to"""
    meetingSurfaces: NotRequired[List[MeetingSurface]]
    """The set of meetingSurfaceItem scopes that a tab belong to"""
    scopes: List[ConfigurableTabScope]
    """Specifies whether the tab offers an experience in the context of a channel in a team, in a 1:1 or group chat, or
    in an experience scoped to an individual user alone. These options are non-exclusive.
    Currently, configurable tabs are only supported in the teams and groupchats scopes."""
    sharePointPreviewImage: NotRequired[str]
    """A relative file path to a tab preview image for use in SharePoint. Size 1024x768."""
    supportedSharePointHosts: NotRequired[List[SupportedSharePointHost]]
    """Defines how your tab will be made available in SharePoint."""


class Connector(TypedDict):
    configurationUrl: NotRequired[str]
    """The url to use for configuring the connector using the inline configuration experience."""
    connectorId: str
    """A unique identifier for the connector which matches its ID in the Connectors Developer Portal."""
    scopes: List[ConnectorScope]
    """Specifies whether the connector offers an experience in the context of a channel in a team, or
    an experience scoped to an individual user alone. Currently, only the team scope is supported."""


class MicrosoftEntraConfiguration(TypedDict):
    """Object capturing details needed to do single aad auth flow. It will be only present when auth type is entraId."""

    supportsSingleSignOn: NotRequired[bool]
    """Boolean indicating whether single sign on is configured for the app."""


class ComposeExtensionAuthorization(TypedDict):
    """Object capturing authorization information."""

    apiSecretServiceAuthConfiguration: NotRequired[APISecretServiceAuthConfiguration]
    """Object capturing details needed to do service auth. It will be only present when
    auth type is apiSecretServiceAuth."""
    authType: NotRequired[AuthType]
    """Enum of possible authentication types."""
    microsoftEntraConfiguration: NotRequired[MicrosoftEntraConfiguration]
    """Object capturing details needed to do single aad auth flow. It will be only present when auth type is entraId."""


class Choice(TypedDict):
    title: str
    """Title of the choice"""
    value: str
    """Value of the choice"""


class Parameter(TypedDict):
    choices: NotRequired[List[Choice]]
    """The choice options for the parameter"""
    description: NotRequired[str]
    """Description of the parameter."""
    inputType: NotRequired[InputType]
    """Type of the parameter"""
    isRequired: NotRequired[bool]
    """The value indicates if this parameter is a required field."""
    name: str
    """Name of the parameter."""
    semanticDescription: NotRequired[str]
    """Semantic description for the parameter."""
    title: str
    """Title of the parameter."""
    value: NotRequired[str]
    """Initial value for the parameter"""


class SamplePrompt(TypedDict):
    text: str
    """This string will hold the sample prompt"""


class ComposeExtensionCommand(TypedDict):
    apiResponseRenderingTemplateFile: NotRequired[str]
    """A relative file path for api response rendering template file."""
    context: NotRequired[List[CommandContext]]
    """Context where the command would apply"""
    description: NotRequired[str]
    """Description of the command."""
    fetchTask: NotRequired[bool]
    """A boolean value that indicates if it should fetch task module dynamically"""
    id: str
    """Id of the command."""
    initialRun: NotRequired[bool]
    """A boolean value that indicates if the command should be run once initially with no parameter."""
    parameters: NotRequired[List[Parameter]]
    samplePrompts: NotRequired[List[SamplePrompt]]
    semanticDescription: NotRequired[str]
    """Semantic description for the command."""
    taskInfo: NotRequired[TaskInfo]
    title: str
    """Title of the command."""
    type: NotRequired[CommandType]
    """Type of the command"""


class Value(TypedDict):
    domains: NotRequired[List[str]]
    """A list of domains that the link message handler can register for,
    and when they are matched the app will be invoked"""
    supportsAnonymizedPayloads: NotRequired[bool]
    """A boolean that indicates whether the app's link message handler supports anonymous invoke flow."""


class MessageHandler(TypedDict):
    type: MessageHandlerType
    """Type of the message handler"""
    value: Value


class ComposeExtension(TypedDict):
    apiSpecificationFile: NotRequired[str]
    """A relative file path to the api specification file in the manifest package."""
    authorization: NotRequired[ComposeExtensionAuthorization]
    """Object capturing authorization information."""
    botId: NotRequired[str]
    """The Microsoft App ID specified for the bot powering the compose extension in the Bot Framework portal (https://dev.botframework.com/bots)"""
    canUpdateConfiguration: NotRequired[Union[bool, None]]
    """A value indicating whether the configuration of a compose extension can be updated by the user."""
    commands: NotRequired[List[ComposeExtensionCommand]]
    composeExtensionType: ComposeExtensionType
    """Type of the compose extension."""
    messageHandlers: NotRequired[List[MessageHandler]]
    """A list of handlers that allow apps to be invoked when certain conditions are met"""


class DeclarativeAgentRef(TypedDict):
    """A reference to a declarative agent element. The element's definition is in a separate file."""

    file: str
    """Relative file path to this declarative agent element file in the application package."""
    id: str
    """A unique identifier for this declarative agent element."""


class CopilotAgents(TypedDict):
    declarativeAgents: List[DeclarativeAgentRef]
    """An array of declarative agent elements references. Currently, only one declarative agent
    per application is supported."""


class DefaultGroupCapability(TypedDict):
    """When a group install scope is selected, this will define the default capability when the user installs the app"""

    groupchat: NotRequired[Groupchat]
    """When the install scope selected is GroupChat, this field specifies the default capability available"""
    meetings: NotRequired[Groupchat]
    """When the install scope selected is Meetings, this field specifies the default capability available"""
    team: NotRequired[Groupchat]
    """When the install scope selected is Team, this field specifies the default capability available"""


class DashboardCardContentSource(TypedDict):
    """Represents a configuration for the source of the card's content."""

    botConfiguration: NotRequired[BotConfiguration]
    """The configuration for the bot source. Required if sourceType is set to bot."""
    sourceType: NotRequired[SourceType]
    """The content of the dashboard card is sourced from a bot."""


class DashboardCardIcon(TypedDict):
    """Represents a configuration for the source of the card's content"""

    iconUrl: NotRequired[str]
    """The icon for the card, to be displayed in the toolbox and card bar, represented as URL."""
    officeUIFabricIconName: NotRequired[str]
    """Office UI Fabric/Fluent UI icon friendly name for the card. This value will be used
    if 'iconUrl' is not specified."""


class DashboardCard(TypedDict):
    """Cards wich could be pinned to dashboard providing summarized view of information relevant to user."""

    contentSource: DashboardCardContentSource
    defaultSize: DefaultSize
    """Rendering Size for dashboard card."""
    description: str
    """Description of the card.Maximum length is 255 characters."""
    displayName: str
    """Represents the name of the card. Maximum length is 255 characters."""
    icon: NotRequired[DashboardCardIcon]
    id: str
    """Unique Id for the card. Must be unique inside the app."""
    pickerGroupId: str
    """Id of the group in the card picker. This must be guid."""


class Developer(TypedDict):
    mpnId: NotRequired[str]
    """The Microsoft Partner Network ID that identifies the partner organization building the app.
    This field is not required, and should only be used if you are already part of the Microsoft Partner Network.
    More info at https://aka.ms/partner"""
    name: str
    """The display name for the developer."""
    privacyUrl: str
    """The url to the p
    age that provides privacy information for the app."""
    termsOfUseUrl: str
    """The url to the page that provides the terms of use for the app."""
    websiteUrl: str
    """The url to the page that provides support information for the app."""


class Capability(TypedDict):
    maxVersion: NotRequired[str]
    """Identifies the maximum version for the requirement sets that the add-in needs to run."""
    minVersion: NotRequired[str]
    """Identifies the minimum version for the requirement sets that the add-in needs to run."""
    name: str
    """Identifies the name of the requirement sets that the add-in needs to run."""


class RequirementsExtensionElement(TypedDict):
    capabilities: NotRequired[List[Capability]]
    formFactors: NotRequired[List[FormFactor]]
    """Identifies the form factors that support the add-in. Supported values: mobile, desktop."""
    scopes: NotRequired[List[RequirementsScope]]
    """Identifies the scopes in which the add-in can run."""


class Prefer(TypedDict):
    comAddin: NotRequired[COMAddin]


class CustomOfficeAddin(TypedDict):
    officeAddinId: str
    """Solution ID of the in-market add-in to hide. Maximum length is 64 characters."""


class StoreOfficeAddin(TypedDict):
    assetId: str
    """Asset ID of the in-market add-in to hide. Maximum length is 64 characters."""
    officeAddinId: str
    """Solution ID of an in-market add-in to hide. Maximum length is 64 characters."""


class Hide(TypedDict):
    customOfficeAddin: NotRequired[CustomOfficeAddin]
    storeOfficeAddin: NotRequired[StoreOfficeAddin]


class ExtensionAlternateVersionsArray(TypedDict):
    alternateIcons: NotRequired[AlternateIcons]
    hide: NotRequired[Hide]
    prefer: NotRequired[Prefer]
    requirements: NotRequired[RequirementsExtensionElement]


class Options(TypedDict):
    """Configures how Outlook responds to the event."""

    sendMode: SendMode


class Event(TypedDict):
    actionId: str
    """The ID of an action defined in runtimes. Maximum length is 64 characters."""
    options: NotRequired[Options]
    """Configures how Outlook responds to the event."""
    type: str


class ExtensionAutoRunEventsArray(TypedDict):
    events: List[Event]
    """Specifies the type of event. For supported types,
    please see: https://review.learn.microsoft.com/en-us/office/dev/add-ins/outlook/autolaunch?tabs=xmlmanifest#supported-events."""
    requirements: NotRequired[RequirementsExtensionElement]


class ExtensionCustomMobileIcon(TypedDict):
    scale: int
    """How to scale - 1,2,3 for each image. This attribute specifies the UIScreen.scale property for iOS devices."""
    size: int
    """Size in pixels of the icon. Three image sizes are required (25, 32, and 48 pixels)."""
    url: str
    """Url to the icon."""


class ExtensionRibbonsCustomMobileControlButtonItem(TypedDict):
    actionId: str
    """The ID of an action defined in runtimes. Maximum length is 64 characters."""
    icons: List[ExtensionCustomMobileIcon]
    id: str
    """Specify the Id of the button like msgReadFunctionButton."""
    label: str
    """Short label of the control. Maximum length is 32 characters."""
    type: PurpleType


class ExtensionRibbonsCustomMobileGroupItem(TypedDict):
    controls: List[ExtensionRibbonsCustomMobileControlButtonItem]
    id: str
    """Specify the Id of the group. Used for mobileMessageRead ext point."""
    label: str
    """Short label of the control. Maximum length is 32 characters."""


class ExtensionCommonSuperToolTip(TypedDict):
    description: str
    """Description of the super tip. Maximum length is 250 characters."""
    title: str
    """Title text of the super tip. Maximum length is 64 characters."""


class ExtensionCommonCustomControlMenuItem(TypedDict):
    actionId: str
    """The ID of an action defined in runtimes. Maximum length is 64 characters."""
    enabled: NotRequired[bool]
    """Whether the control is initially enabled."""
    icons: NotRequired[List[ExtensionCommonIcon]]
    id: str
    """A unique identifier for this control within the app. Maximum length is 64 characters."""
    label: str
    """Displayed text for the control. Maximum length is 64 characters."""
    overriddenByRibbonApi: NotRequired[bool]
    supertip: ExtensionCommonSuperToolTip
    type: ItemType
    """Supported values: menuItem."""


class ExtensionCommonCustomGroupControlsItem(TypedDict):
    actionId: str
    """The ID of an execution-type action that handles this key combination. Maximum length is 64 characters."""
    builtInControlId: NotRequired[str]
    """Id of the existing office control. Maximum length is 64 characters."""
    enabled: NotRequired[bool]
    """Whether the control is initially enabled."""
    icons: NotRequired[List[ExtensionCommonIcon]]
    id: str
    """A unique identifier for this control within the app. Maximum length is 64 characters."""
    items: NotRequired[List[ExtensionCommonCustomControlMenuItem]]
    """Configures the items for a menu control."""
    label: str
    """Displayed text for the control. Maximum length is 64 characters."""
    overriddenByRibbonApi: NotRequired[bool]
    """Specifies whether a group, button, menu, or menu item will be hidden on application and platform combinations
    that support the API (Office.ribbon.requestCreateControls) that installs custom contextual tabs on the ribbon.
    Default is false."""
    supertip: ExtensionCommonSuperToolTip
    type: FluffyType
    """Defines the type of control whether button or menu."""


class ExtensionRibbonsCustomTabGroupsItem(TypedDict):
    builtInGroupId: NotRequired[str]
    """Id of a built-in Group. Maximum length is 64 characters."""
    controls: NotRequired[List[ExtensionCommonCustomGroupControlsItem]]
    icons: NotRequired[List[ExtensionCommonIcon]]
    id: NotRequired[str]
    """A unique identifier for this group within the app. Maximum length is 64 characters."""
    label: NotRequired[str]
    """Displayed text for the group. Maximum length is 64 characters."""


class Position(TypedDict):
    align: Align
    """Define alignment of this custom tab relative to the specified built-in tab."""
    builtInTabId: str
    """The id of the built-in tab. Maximum length is 64 characters."""


class ExtensionRibbonsArrayTabsItem(TypedDict):
    builtInTabId: NotRequired[str]
    """Id of the existing office Tab. Maximum length is 64 characters."""
    customMobileRibbonGroups: NotRequired[List[ExtensionRibbonsCustomMobileGroupItem]]
    """Defines mobile group item."""
    groups: NotRequired[List[ExtensionRibbonsCustomTabGroupsItem]]
    """Defines tab groups."""
    id: NotRequired[str]
    """A unique identifier for this tab within the app. Maximum length is 64 characters."""
    label: NotRequired[str]
    """Displayed text for the tab. Maximum length is 64 characters."""
    position: NotRequired[Position]


class ExtensionRibbonsArray(TypedDict):
    contexts: NotRequired[List[ExtensionContext]]
    requirements: NotRequired[RequirementsExtensionElement]
    tabs: List[ExtensionRibbonsArrayTabsItem]


class ExtensionRuntimeCode(TypedDict):
    page: str
    """URL of the .html page to be loaded in browser-based runtimes."""
    script: NotRequired[str]
    """URL of the .js script file to be loaded in UI-less runtimes."""


class Name(TypedDict):
    full: str
    """The full name of the app, used if the full app name exceeds 30 characters."""
    short: str
    """A short display name for the app."""


class ExtensionRuntimesActionsItem(TypedDict):
    """Specifies the set of actions supported by this runtime. An action is either running a JavaScript function or
    opening a view such as a task pane."""

    displayName: NotRequired[str]
    """Display name of the action. Maximum length is 64 characters."""
    id: str
    """Identifier for this action. Maximum length is 64 characters. This value is passed to the code file."""
    multiselect: NotRequired[bool]
    """Whether allows the action to have multiple selection."""
    pinnable: NotRequired[bool]
    """Specifies that a task pane supports pinning, which keeps the task pane open when
    the user changes the selection."""
    supportsNoItemContext: NotRequired[bool]
    """Whether allows task pane add-ins to activate without the Reading Pane enabled or a message selected."""
    type: ActionType
    """executeFunction: Run a script function without waiting for it to finish. openPate: Open a page in a view."""
    view: NotRequired[str]
    """View where the page should be opened. Maximum length is 64 characters."""


class ExtensionRuntimesArray(TypedDict):
    """A runtime environment for a page or script"""

    actions: NotRequired[List[ExtensionRuntimesActionsItem]]
    code: ExtensionRuntimeCode
    id: str
    """A unique identifier for this runtime within the app.  Maximum length is 64 characters."""
    lifetime: NotRequired[Lifetime]
    """Runtimes with a short lifetime do not preserve state across executions. Runtimes with a long lifetime do."""
    requirements: NotRequired[RequirementsExtensionElement]
    type: NotRequired[RuntimeType]
    """Supports running functions and launching pages."""


class ElementExtension(TypedDict):
    """The set of extensions for this app. Currently only one extensions per app is supported."""

    alternates: NotRequired[List[ExtensionAlternateVersionsArray]]
    audienceClaimUrl: NotRequired[str]
    """The url for your extension, used to validate Exchange user identity tokens."""
    autoRunEvents: NotRequired[List[ExtensionAutoRunEventsArray]]
    requirements: NotRequired[RequirementsExtensionElement]
    ribbons: NotRequired[List[ExtensionRibbonsArray]]
    runtimes: NotRequired[List[ExtensionRuntimesArray]]


class GraphConnector(TypedDict):
    """Specify the app's Graph connector configuration. If this is present then
    webApplicationInfo.id must also be specified."""

    notificationUrl: str
    """The url where Graph-connector notifications for the application should be sent."""


class LocalizationInfo(TypedDict):
    additionalLanguages: NotRequired[List[AdditionalLanguage]]
    defaultLanguageFile: NotRequired[str]
    """A relative file path to a the .json file containing strings in the default language."""
    defaultLanguageTag: str
    """The language tag of the strings in this top level manifest file."""


class ResourceSpecific(TypedDict):
    name: str
    """The name of the resource-specific permission."""
    type: ResourceSpecificType
    """The type of the resource-specific permission: delegated vs application."""


class Permissions(TypedDict):
    """List of permissions that the app needs to function."""

    resourceSpecific: NotRequired[List[ResourceSpecific]]
    """Permissions that must be granted on a per resource instance basis."""


class ManifestAuthorization(TypedDict):
    """Specify and consolidates authorization related information for the App."""

    permissions: NotRequired[Permissions]
    """List of permissions that the app needs to function."""


class Scene(TypedDict):
    file: str
    """A relative file path to a scene metadata json file."""
    id: str
    """A unique identifier for this scene. This id must be a GUID."""
    maxAudience: int
    """Maximum audiences supported in scene."""
    name: str
    """Scene name."""
    preview: str
    """A relative file path to a scene PNG preview icon."""
    seatsReservedForOrganizersOrPresenters: int
    """Number of seats reserved for organizers or presenters."""


class MeetingExtensionDefinition(TypedDict):
    """Specify meeting extension definition."""

    scenes: NotRequired[List[Scene]]
    """Meeting supported scenes."""
    supportsAnonymousGuestUsers: NotRequired[bool]
    """A boolean value indicating whether this app allows management by anonymous users."""
    supportsStreaming: NotRequired[bool]
    """A boolean value indicating whether this app can stream the meeting's audio video content to an RTMP endpoint."""


class StaticTab(TypedDict):
    contentBotId: NotRequired[str]
    """The Microsoft App ID specified for the bot in the Bot Framework portal (https://dev.botframework.com/bots)"""
    contentUrl: NotRequired[str]
    """The url which points to the entity UI to be displayed in the canvas."""
    context: NotRequired[List[StaticTabContext]]
    """The set of contextItem scopes that a tab belong to"""
    entityId: str
    """A unique identifier for the entity which the tab displays."""
    name: NotRequired[str]
    """The display name of the tab."""
    scopes: List[CommandListScope]
    """Specifies whether the tab offers an experience in the context of a channel in a team, or
    an experience scoped to an individual user alone or group chat. These options are non-exclusive.
    Currently static tabs are only supported in the 'personal' scope."""
    searchUrl: NotRequired[str]
    """The url to direct a user's search queries."""
    websiteUrl: NotRequired[str]
    """The url to point at if a user opts to view in a browser."""


class SubscriptionOffer(TypedDict):
    """Subscription offer associated with this app."""

    offerId: str
    """A unique identifier for the Commercial Marketplace Software as a Service Offer."""


class WebApplicationInfo(TypedDict):
    """Specify your AAD App ID and Graph information to help users seamlessly sign into your AAD app."""

    id: str
    """AAD application id of the app. This id must be a GUID."""
    resource: NotRequired[str]
    """Resource url of app for acquiring auth token for SSO."""


class Manifest(TypedDict):
    """Microsoft Teams App Manifest"""

    schema: NotRequired[str]
    """$schema"""

    manifestVersion: ManifestVersion
    """The version of the schema this manifest is using. This schema version supports extending Teams apps to
    other parts of the Microsoft 365 ecosystem. More info at https://aka.ms/extendteamsapps."""

    version: str
    """The version of the app. Changes to your manifest should cause a version change.
    This version string must follow the semver standard (http://semver.org)."""

    id: str
    """A unique identifier for this app. This id must be a GUID."""

    developer: Developer
    """Specifies information about your company.
    For apps submitted to the Teams Store, these values must match the information in Teams Store listing."""

    name: Name
    """The name of your app experience, displayed to users in the Teams experience. For apps submitted to AppSource,
    these values must match the information in your AppSource entry."""

    description: Description
    """Describes your app to users. For apps submitted to AppSource, these values must match the information
    in your AppSource entry"""

    localizationInfo: NotRequired[LocalizationInfo]
    """Allows the specification of a default language, and pointers to additional language files."""

    icons: Icons
    """Icons used within the Teams app. The icon files must be included as part of the upload package"""

    accentColor: str
    """A color to use in conjunction with the icon.
    The value must be a valid HTML color code starting with '#', for example `#4464ee`."""

    copilotAgents: NotRequired[CopilotAgents]
    """Defines one or more agents to Microsoft 365 Copilot."""

    configurableTabs: NotRequired[List[ConfigurableTab]]
    """These are tabs users can optionally add to their channels and 1:1 or group chats and require extra configuration
    before they are added. Configurable tabs are not supported in the personal scope. Currently only one configurable
    tab per app is supported."""

    staticTabs: NotRequired[List[StaticTab]]
    """A set of tabs that may be 'pinned' by default, without the user adding them manually.
    Static tabs declared in personal scope are always pinned to the app's personal experience.
    Static tabs do not currently support the 'teams' scope."""

    bots: NotRequired[List[Bot]]
    """The set of bots for this app. Currently only one bot per app is supported."""

    connectors: NotRequired[List[Connector]]
    """The set of Office365 connectors for this app. Currently only one connector per app is supported."""

    composeExtensions: NotRequired[List[ComposeExtension]]
    """The set of compose extensions for this app. Currently only one compose extension per app is supported."""

    permissions: NotRequired[List[Permission]]
    """Specifies the permissions the app requests from users."""

    devicePermissions: NotRequired[List[DevicePermission]]
    """Specify the native features on a user's device that your app may request access to."""

    validDomains: NotRequired[List[str]]
    """A list of valid domains from which the tabs expect to load any content.
    Domain listings can include wildcards, for example `*.example.com`.
    If your tab configuration or content UI needs to navigate to any other domain
    besides the one use for tab configuration, that domain must be specified here."""

    webApplicationInfo: NotRequired[WebApplicationInfo]
    """Specify your AAD App ID and Graph information to help users seamlessly sign into your AAD app."""

    graphConnector: NotRequired[GraphConnector]
    """Specify the app's Graph connector configuration.
    If this is present then webApplicationInfo.id must also be specified."""

    showLoadingIndicator: NotRequired[bool]
    """A value indicating whether or not show loading indicator when app/tab is loading"""

    isFullScreen: NotRequired[bool]
    """A value indicating whether a personal app is rendered without a tab header-bar"""

    activities: NotRequired[Activities]

    defaultGroupCapability: NotRequired[DefaultGroupCapability]
    """When a group install scope is selected, this will define the default capability when the user installs the app"""

    defaultInstallScope: NotRequired[DefaultInstallScope]
    """The install scope defined for this app by default. This will be the option displayed on the button
    when a user tries to add the app"""

    configurableProperties: NotRequired[List[ConfigurableProperty]]
    """A list of tenant configured properties for an app"""

    supportedChannelTypes: NotRequired[List[SupportedChannelType]]
    """List of 'non-standard' channel types that the app supports.
    Note: Channels of standard type are supported by default if the app supports team scope."""

    defaultBlockUntilAdminAction: NotRequired[bool]
    """A value indicating whether an app is blocked by default until admin allows it"""

    publisherDocsUrl: NotRequired[str]
    """The url to the page that provides additional app information for the admins"""

    subscriptionOffer: NotRequired[SubscriptionOffer]
    """Subscription offer associated with this app."""

    meetingExtensionDefinition: NotRequired[MeetingExtensionDefinition]
    """Specify meeting extension definition."""

    authorization: NotRequired[ManifestAuthorization]
    """Specify and consolidates authorization related information for the App."""

    extensions: NotRequired[List[ElementExtension]]
    """The extensions property specifies Outlook Add-ins within an app manifest.
    """
    dashboardCards: NotRequired[List[DashboardCard]]
    """Defines the list of cards which could be pinned to dashboards that can provide
    summarized view of information relevant to user."""


class PartialManifest(Manifest, total=False):
    pass
