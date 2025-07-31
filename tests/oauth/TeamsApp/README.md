# Microsoft 365 Agents Toolkit Configuration: Oauth

Use this if you want to enable user authentication in your Teams application.

## Welcome to Microsoft 365 Agents Toolkit!

### Pre-requisites

- [Visual Studio v17.14.0 or above](https://visualstudio.microsoft.com/vs/)
- [Microsoft 365 Agents Toolkit Extension for Visual Studio](https://learn.microsoft.com/en-us/microsoftteams/platform/toolkit/toolkit-v4/install-teams-toolkit-vs)

### Quick Start

1. In the debug dropdown menu, select Dev Tunnels > Create A Tunnel (set authentication type to Public) or select an existing public dev tunnel
</br>![image](https://raw.githubusercontent.com/OfficeDev/TeamsFx/dev/docs/images/visualstudio/debug/create-devtunnel-button.png)
2. Right-click the 'TeamsApp' project in Solution Explorer and select **Microsoft 365 Agents Toolkit > Select Microsoft 365 Account**
3. Sign in to Microsoft 365 Agents Toolkit with a **Microsoft 365 work or school account**
4. Configure the Launch profile to be `Microsoft Teams (Browser)`.
5. Press F5, or select Debug > Start Debugging menu in Visual Studio to start your app.
</br>![image](https://raw.githubusercontent.com/OfficeDev/TeamsFx/dev/docs/images/visualstudio/debug/debug-button.png)
5. In the opened web browser, select Add button to install the app in Teams.


### Get more info

New to Teams app development or Microsoft 365 Agents Toolkit? Explore Teams app manifests, cloud deployment, and much more in the https://aka.ms/teams-toolkit-vs-docs.

### Report an issue

Select Visual Studio > Help > Send Feedback > Report a Problem. 
Or, create an issue directly in our GitHub repository:
https://github.com/OfficeDev/TeamsFx/issues

## How to update scopes

1. In the `aad.manifest.json` file, update the `requiredResourceAccess` list to add the required scopes.

2. In the `infra/botRegistration/azurebot.bicep` file, under the `botServicesMicrosoftGraphConnection` resource, update the `properties.scopes` string to be a comma-delimeted list of the required scopes.

### Example

If you want to add the `People.Read.All` and `User.ReadBasic.All` scopes.

1. Your `requiredResourceAccess` property should look like:

```json
"requiredResourceAccess": [
    {
        "resourceAppId": "Microsoft Graph",
        "resourceAccess": [
            {
                "id": "People.Read.All",
                "type": "Scope"
            }
        ]
    },
    {
        "resourceAppId": "Microsoft Graph",
        "resourceAccess": [
            {
                "id": "User.ReadBasic.All",
                "type": "Scope"
            }
        ]
    },
]
```

2. Update the `properties.scopes` to be `People.Read.All,User.ReadBasic.All`.
