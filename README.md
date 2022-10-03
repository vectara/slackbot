# What is it
This is a bot for [Slack](https://slack.com/) which indexes messages into
[Vectara's](http://vectara.com/) platform and makes them available for Search.

The difference between this and Slack's built-in search capabilities is that
this adds interactive semantic/neural search capabilities.  You ask the bot a
question and it returns a link to what it knows, as well as interactive filters
for dates, channels, and/or people.  It performs the search in public, allowing
all users to see the relevant result(s) at the same time.

This particular bot is primarily intended as a demonstration of the Vectara
platform, but can be used practically to add multi-lingual neural search to
your Slack workspace.

For an example of what this bot can do, see the following, which has no
substantial keyword overlap:

![Example Search](img/example.png)

# How to use it
Have a look at [setup.md](setup.md) for instructions on how to set up the bot.
After you have it set up, invite it to one or more channels.  After it's been
added, continue using the Slack channel(s) as normal.  If you want to perform a
search, send a message in the channel to `@your_bot_name` and it will respond
with the top search result.

# Limitations
This Slackbot is currently *mostly* intended to be an example of how to
use/interact with the Vectara platform via the APIs and with a more
conversational feel than many search engines.  However, there are some
limitations which are worth noting if you're going to use this, many of which
we'd like to address over time.

Current limitations include:
- The bot doesn't index any content that was created *prior* to the
bot being invited to the channel.  So it's not yet possible to search
"historic" content.
- The bot doesn't index images or files.  Vectara's platform does
support indexing files, but the Slack-specific interactions and file indexing
have not been added.
- The bot doesn't keep/index threads/contexts.  So if you're responding to a
message, it doesn't currently know that something was a response or what
messages were added to a thread
- Slack does not send/resolve any usernames or channel names directly.  This
helps preserve some anonymity, but means you can't ask it "What did Shane say
about foo?"
- Messages for "Growth" plan users are not instantly indexed, but instead
may undergo a delay from message time to indexing.  So searches for very recent
messages may fail/produce irrelevant results until the recent message is
indexed.

Pull requests are welcome for the above or any other issues/enhancements!