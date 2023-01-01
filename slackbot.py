import json
import logging
import os
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from vectara_functions import get_metadata_value, index_message, search, search_raw
from slack_helpers import homepage_blocks, escape_markdown

app = App(token=os.environ.get('SLACK_BOT_TOKEN'))

def get_channel_filter(channel):
  return 'doc.channel = \'{}\''.format(channel)

def get_user_filter(user):
  return 'doc.poster = \'{}\''.format(user)

def get_start_date_filter(date):
  utc_time = datetime.strptime(date, "%Y-%m-%d")
  epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
  return 'doc.timestamp >= {}'.format(epoch_time)

def get_end_date_filter(date):
  utc_time = datetime.strptime(date, "%Y-%m-%d")
  epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
  return 'doc.timestamp <= {}'.format(epoch_time)

def extract_filters_from_state(state):
  filter_values = []
  if state != None:
      for block in state['values']:
        filters = state['values'][block]
        for filter in filters:
          if filter == 'filter_by_channel' and state['values'][block][filter]['selected_channel'] != None:
            filter_values['channel'] = get_channel_filter(state['values'][block][filter]['selected_channel'])
          elif filter == 'filter_by_user' and state['values'][block][filter]['selected_user'] != None:
            filter_values['user'] = get_user_filter(state['values'][block][filter]['selected_user'])
          elif filter == 'filter_start_date':
            filter_values['start_date'] = get_start_date_filter(state['values'][block][filter]['selected_date'])
          elif filter == 'filter_end_date':
            filter_values['end_date'] = get_end_date_filter(state['values'][block][filter]['selected_date'])
  return filter_values

def get_original_query_text(message):
  """Extracts the original query text by looking up"""
  # TODO: create a better way to grab the original query text
  for b in message['blocks']:
    if 'text' in b and 'text' in b['text'] and b['text']['text'].startswith('Search results for:'):
      original_text = b['text']['text'].replace('Search results for: ','')
      original_text = original_text.strip('*')
      return original_text
  return None

def standard_query_and_filter(ack, body, say, logger, extract_filters_from_state = True):
  """Helper function for most of the filters.
  - Extracts the filter state
  - Pulls the original query text
  - Performs the search
  - Responds to the user
  """
  ack()
  user = None
  channel = None
  start_date = None
  end_date = None
  if extract_filters_from_state:
    filters = extract_filters_from_state(body['state'])
    user = filters['user'] if 'user' in filters else None
    channel = filters['channel'] if 'channel' in filters else None
    start_date = filters['start_date'] if 'start_date' in filters else None
    end_date = filters['end_date'] if 'end_date' in filters else None

  original_search = get_original_query_text(body['message'])
  query_and_respond(say, original_search,
                    start_date=start_date, end_date=end_date,
                    filter_by_user=user, filter_by_channel=channel)

@app.action("filter_by_channel")
def filter_by_channel(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered to a specific channel."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_by_user")
def filter_by_user(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered to a specific user."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_start_date")
def filter_by_start_date(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered >= some date."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_end_date")
def filter_by_end_date(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered <= some date."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("more_results")
def more_results(ack, body, say, logger):
  """Triggered when a user asks for more results."""
  ack()
  state = body['state']
  original_search = get_original_query_text(body['message'])
  query_and_respond(say, original_search, state=state, num_results = 2)

@app.command("/vectara")
def command_search(ack, respond, command):
    ack()
    text = command['text']
    channel = None
    user = None
    parts = text.split(' ', 1)
    if parts[0].startswith('<'):
      channel_or_user = parts[0]
      channel_or_user_parts = channel_or_user.split('|')
      channel_or_user_id = channel_or_user_parts[0]
      # channel is e.g. <#C03V4NCQJK2|foo-bar>.  can also be a person if it starts with @ e.g. <@C03V4NCQJK2|shane>
      if channel_or_user_id.startswith('<@'):
        user = get_user_filter(channel_or_user_id[2:])
      elif channel_or_user_id.startswith('<#'):
        channel = get_channel_filter(channel_or_user_id[2:])
      text = parts[1]
    query_and_respond(respond, search_text = text,
                      filter_by_user=user, filter_by_channel=channel)

@app.event('app_home_opened')
def home(client, event, logger):
  client.views_publish(
      # the user that opened your app's app home
      user_id=event["user"],
      # the view object that appears in the app home
      view={
        "type": "home",
        "callback_id": "home_view",

        # body of the view
        "blocks": homepage_blocks()
      }
    )

@app.event('message')
def read_message(message, context, say):
  """Triggered when a message is posted.

  This function looks for the bot's username, and if it's in the message, it
  assumes the user wants to search and it extracts this as search text.
  Otherwise, simply index the content
  """
  bot_user_id = context['bot_user_id']

  if 'text' in message:
    message_text = message['text']
    bot_user_id_reference = '<@{}>'.format(bot_user_id) #this is how a bot's mention shows up in the text

    if (message['channel_type'] == 'im'):
      # this is a search request -- either a direct message to the bot or the bot is mentioned
      search_text = message_text.replace(bot_user_id_reference,"").strip()
      query_and_respond(say, search_text)
    elif message['channel_type'] == 'channel':
      if bot_user_id_reference in message_text:
        search_text = message_text.replace(bot_user_id_reference,"").strip()
        query_and_respond(say, search_text, filter_by_channel=get_channel_filter(message['channel']))
      else:
        #index the content
        epoch_us = int(float(message['event_ts']) * 10000000)
        link = 'https://{}.slack.com/archives/{}/p{}'.format(
          os.environ.get('SLACK_WORKSPACE_SUBDOMAIN'),
          message['channel'],
          epoch_us
        )
        metadata = {
          "message_link": link,
          "message_type": message['type'],
          "poster": message['user'],
          "channel": message['channel'],
          "channel_type": message['channel_type'],
          "timestamp": float(message['event_ts'])
        }

        index_message(
          customer_id=int(os.environ.get('VECTARA_CUSTOMER_ID')),
          corpus_id=int(os.environ.get('VECTARA_CORPUS_ID')),
          text=message_text,
          id=message['client_msg_id'],
          title="Message from <@{}> at {}".format(message['user'], message['event_ts']),
          metadata=metadata
        )
  else:
    logging.error("Unhandled channel type: %s",message['channel_type'])

def query_and_respond(say, search_text = None, rerank = None,
                      start_date = None, end_date = None, filter_by_user = None,
                      filter_by_channel = None, num_results = 1):
    """
    """
    if rerank == None and os.environ.get('VECTARA_USE_RERANKER') == 'true':
      rerank = True
    filters = [x for x in [filter_by_channel, filter_by_user, start_date, end_date] if x is not None]
    
    search_query, search_results = search(search_text=search_text,
                                          rerank=rerank,
                                          num_results=num_results,
                                          metadata_filters=filters)
    
    if (len(search_results['responseSet']) > 0 and len(search_results['responseSet'][0]['response']) > 0):
      # Always grab the last result, because if the user has asked for
      # "more results", we set the search size and then look at the last result
      response = search_results['responseSet'][0]['response'][-1]
      text = response['text']
      document = search_results['responseSet'][0]['document'][-1]
      response_metadata = response['metadata']
      document_metadata = document['metadata']
      text = escape_markdown(text)
      
      # Grab the metadata from Vectara's response
      link_meta = get_metadata_value(document_metadata, 'message_link')
      poster = get_metadata_value(document_metadata, 'poster')
      channel = get_metadata_value(document_metadata, 'channel')
      timestamp = get_metadata_value(document_metadata, 'timestamp')

      # blocks are Slack's way of formatting messages.  For a reference, see
      # https://app.slack.com/block-kit-builder/
      blocks = [
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "Search results for: *{}*".format(search_text)
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "fields": [
            {
                "type": "mrkdwn",
                "text": "<@{}> said:\n> {}".format(poster, text)
            }
          ]
        },
        {
          "type": "section",
          "text": { "type": "mrkdwn", "text": "<{}|Link>".format(link_meta) }
        }
      ]

      # Only add the reranker / more results, and filters if the user hasn't
      # already used one of them.  This is an arbitrary limitation that just
      # simplifies some logic and can be removed in the future
      if len(filters) == 0:
        blocks.append({
            "type": "divider"
        })
        # Add our metadata filters
        blocks.append({
          "type": "section",
          "text": { "type": "mrkdwn", "text": "User and Channel Filters:" }
        })
        blocks.append({
          "type": "actions",
          "elements": [
            {
              "type": "users_select",
              "placeholder": {
                "type": "plain_text",
                "text": "Filter by user",
                "emoji": True
              },
              "action_id": "filter_by_user"
            },
            {
              "type": "channels_select",
              "placeholder": {
                "type": "plain_text",
                "text": "Filter by channel",
                "emoji": True
              },
              "action_id": "filter_by_channel"
            }
          ]
        })
        blocks.append({
          "type": "section",
          "text": { "type": "mrkdwn", "text": "Minimum and Maximum Post Time Filters:" }
        })
        blocks.append({
          "type": "actions",
          "elements": [
            {
              "type": "datepicker",
              "initial_date": "2022-09-01",
              "placeholder": {
                "type": "plain_text",
                "text": "Start Date",
                "emoji": True
              },
              "action_id": "filter_start_date"
            },
            {
              "type": "datepicker",
              "initial_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
              "placeholder": {
                "type": "plain_text",
                "text": "End Date",
                "emoji": True
              },
              "action_id": "filter_end_date"
            }
          ]
        })
        blocks.insert(0, {
          "type": "header",
          "text": {
            "type": "plain_text",
            "text": "Search Results"
          }
        })
      else:
        if num_results != 1:
          blocks.insert(0, {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "Search Results (Result {})".format(num_results)
            }
          })
      say(blocks=blocks, text="@{} said:\n> {}\n\n at {}".format(poster,text,timestamp), unfurl_links=False, unfurl_media=False)
    else:
      say("Sorry, I couldn't find any relevant results")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get('SLACK_APP_TOKEN'))
    handler.start()
