In oroder to set up an instance of this Slack bot, you'll need to do a few
things first.

# Clone This Repo and Add Dependencies
Once you've cloned this repo, the Python package requirements can be found in
[requirements.txt](requirements.txt).  Install these packages before
continuing.

# Get a Vectara Account
If you don't already have a [Vectara](https://vectara.com) account, you'll need
one, so go there and sign up first.  The bot uses Vectara for search and
filtering capabilities.

## Customer ID
Your Vectara customer ID to will be in your welcome e-mail from Vectara.
Alternatively, you can copy it by clicking your username in the upper-right
hand corner of the product console.  Once you've got this number, paste it into
`start.sh` in the value for VECTARA_CUSTOMER_ID

## Corpus Creation
From [Vectara](https://console.vectara.com), create a new corpus.  This corpus
will hold the content for our Slack messages.

- Name the corpus anything of your choosing
- In the section "Filter Attributes:
  -  Add a new filter attibute with `Name` of `poster`, `level` of `Document`
  and `Data Type` of `Text`
  -  Add a new filter attibute with `Name` of `channel`, `level` of `Document`
  and `Data Type` of `Text`
  -  Add a new filter attibute with `Name` of `timestamp`, `level` of
  `Document` and `Data Type` of `Float`
- Optionally, give the corpus a description

Once you've created the corpus, navigate to it and copy the `ID` value to
`VECTARA_CORPUS_ID` in `start.sh`

## Vectara Authentication
Go to [Vectara's Authentication](https://console.vectara.com/console/authentication)

Create a new App Client and give it any name/description of your choosing.  You
can leave all other fields at their default values.

Once you've created the app client, copy the string in the table under the name
of the app client and paste it to `VECTARA_APP_ID` in `start.sh`

Next, click the `...` on the right, go to "Show Secret."  Copy the secret value
add paste to `VECTARA_APP_SECRET` in `start.sh`

## Corpus Authorization
Go back to the corpus you created in the `Corpus Creation` step and go to the
Authorization tab. Click "Create Role" and select the App Client you created
in the previous step. Give it `ADM` permissions to be able to both index and
search the corpus.

# Create a New Slack App
Go to https://api.slack.com/apps?new_app=1 and create an app "From scratch."
Name the app whatever you want, and select a workspace that you intend to
install it to.

Once you've done this, click "Create App."

# Slack App Settings

## Socket Mode
Under `Settings` in the navigation bar, select `Socket Mode` and toggle *ON*
socket mode for this application.

When you enable Socket Mode, Slack will give you an application token that our
bot will need.  This token will typically start with `xapp`.  Copy this token
and set it in `start.sh` as the value for `SLACK_APP_TOKEN`.

## Event Subscriptions
Under `Features` in the navigation bar, select `Event Subscriptions` and ensure
`Enable Events` is turned *ON*.  The navigate to the section under "Subscribe
to bot events" and add subscriptions for:
- message.groups
- message.im
- message.channels

Once you've done this, click "Save Changes"

## OAuth & Permissions
Under `Features` in the navigation bar, go to `OAuth & Permissions`.

You'll need to enable the `chat:write` permission under the `Scopes` section.

After you've done this, install the app in Slack by going to `Install App`
under `Settings` in the navigation bar.  Copy the OAuth token value that's
provided to you when you install.  It generally starts with `xoab`.  Paste the
value o fthis into the `SLACK_BOT_TOKEN` value in `start.sh`

## Workspace
Set your Slack workspace as `SLACK_WORKSPACE_SUBDOMAIN` in `start.sh`.  For
example, if you log into Slack as `foo.slack.com`, then your
`SLACK_WORKSPACE_SUBDOMAIN` would be `foo`

## Invite
The last step in Slack is to invite the bot to channels you want to be
searchable.
