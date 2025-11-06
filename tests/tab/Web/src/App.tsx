import React from 'react';
import * as teamsJs from '@microsoft/teams-js';
import * as client from '@microsoft/teams.client';
import * as endpoints from '@microsoft/teams.graph-endpoints';
import { ConsoleLogger } from '@microsoft/teams.common';

import './App.css';

const clientId = import.meta.env.VITE_CLIENT_ID;

export default function App() {
  const [content, setContent] = React.useState('');
  const [app, setApp] = React.useState<client.App | null>(null);

  React.useEffect(() => {
    (async () => {
      try {
          // initialize the app and prompt for Graph scope consent, if not already granted
          const app = new client.App(clientId, {
            logger: new ConsoleLogger('@tests/tab', { level: 'debug' }),
              msalOptions: {
              prewarmScopes: [
                'https://graph.microsoft.com/User.Read',
                'https://graph.microsoft.com/Presence.Read',
                'https://graph.microsoft.com/Presence.ReadWrite'
              ]
            }
          });

          await app.start();
          app.log.info('app started');
          setApp(app);
        } catch (err) {
          console.error(err);
        }
    })();
  }, []);

  const showTeamsJsContext = React.useCallback(async () => {
    if (!app) {
      return;
    }

    const context = await teamsJs.app.getContext();
    setContent(JSON.stringify(context, null, 2));
  }, [app]);


  const postChatMessage = React.useCallback(async () => {
    if (!app) {
      return;
    }

    // get the bot to post a message to the current chat, whichever that is
    const { conversationId } = await app.exec<{ conversationId: string }>('post-to-chat', { message: 'Hello from the client!' });
    setContent(`Message posted to conversation ${conversationId}`);
  }, [app]);


  const whoAmI = React.useCallback(async () => {
    if (!app) {
      return;
    }

    // get the current user from the Microsoft Graph
    const me = await app.graph.call(endpoints.me.get);
    setContent(JSON.stringify(me, null, 2));
  }, [app]);


  const togglePresentationMode = React.useCallback(async () => {
    if (!app) {
      return;
    }

    // get current presence from the Microsoft Graph
    const { availability } = await app.graph.call(endpoints.me.presence.get);
    const isAvailable = availability === 'Available';

    // toggle between Dnd/Presenting and Available/Available
    const newPresence = {
      sessionId: clientId,
      availability: isAvailable ? 'DoNotDisturb' : 'Available',
      activity: isAvailable ? 'Presenting' : 'Available'
    };
    await app.graph.call(endpoints.me.presence.setPresence.create, newPresence);
    setContent(`You're now ${newPresence.activity}`);

  }, [app]);

  return (
    <div className="App">
      <h1>👋 Welcome</h1>
      <p>This test app lets you try out some of the features offered by Teams AI Library v2 for Teams Tab app developers.</p>

      <div className="actions">
        <button disabled={!app} onClick={showTeamsJsContext}>Show TeamsJs context</button>
        <button disabled={!app} onClick={postChatMessage}>Post chat message</button>
        <button disabled={!app} onClick={whoAmI}>Who am I?</button>
        <button disabled={!app} onClick={togglePresentationMode}>Toggle presentation mode</button>
      </div>

      {content && (
        <div className='result'>
          <pre>
            <code>{content}</code>
          </pre>
        </div>
      )}

      <p>For more information, please refer to the <a href='https://microsoft.github.io/teams-sdk' rel='noopener noreferrer' target='_blank'>Teams AI documentation</a>.</p>
    </div>
  );
}
