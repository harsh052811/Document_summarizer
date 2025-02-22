import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the app with your bot token and signing secret
app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)

# Event listener for messages directed at the bot
@app.event("app_mention")
def handle_app_mention_events(body, say):
    user = body["event"]["user"]
    text = body["event"]["text"]
    say(f"<@{user}> You said: {text}")

if __name__ == "__main__":
    # Start your app
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
