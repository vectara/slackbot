import json
import logging
import os
import re
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from vectara_functions import get_metadata_value, index_message, search, search_raw

app = App(token=os.environ.get('SLACK_BOT_TOKEN'))

# constants
_MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c)
                                             for c in ('*', '`', '_', '~', '|'))
_MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)'
_MARKDOWN_ESCAPE_REGEX = re.compile(r'(?P<markdown>%s|%s)' % (_MARKDOWN_ESCAPE_SUBREGEX, _MARKDOWN_ESCAPE_COMMON))

def get_original_query_text(message):
  """Extracts the original query text by looking up"""
  # TODO: create a better way to grab the original query text
  for b in message['blocks']:
    if 'text' in b and 'text' in b['text'] and b['text']['text'].startswith('Search results for:'):
      original_text = b['text']['text'].replace('Search results for: ','')
      original_text = original_text.strip('*')
      return original_text
  return None

def standard_query_and_filter(ack, body, say, logger):
  """Helper function for most of the filters.
  - Extracts the filter state
  - Pulls the original query text
  - Performs the search
  - Responds to the user
  """
  ack()
  state = body['state']
  original_search = get_original_query_text(body['message'])
  query_and_respond(say, original_search, state=state)

@app.action("filter_by_channel")
def filter_by_channel(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered to a specific channel."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_by_user")
def filter_by_user(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered to a specific user."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_start_date")
def filter_by_channel(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered >= some date."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("filter_end_date")
def filter_by_channel(ack, body, say, logger):
  """Triggered when a user asks for the results to be filtered <= some date."""
  standard_query_and_filter(ack, body, say, logger)

@app.action("enable_reranker")
def enable_reranker(ack, body, say, logger):
  """Triggered when a user asks for results to be reranked."""
  ack()
  state = body['state']
  original_search = get_original_query_text(body['message'])
  query_and_respond(say, original_search, state=state, rerank = True)

@app.action("more_results")
def more_results(ack, body, say, logger):
  """Triggered when a user asks for more results."""
  ack()
  state = body['state']
  original_search = get_original_query_text(body['message'])
  query_and_respond(say, original_search, state=state, num_results = 2)

def escape_markdown(text, *, as_needed=False, ignore_links=True):
    """A helper function that escapes Discord's markdown.

    Parameters
    -----------
    text: :class:`str`
        The text to escape markdown from.
    as_needed: :class:`bool`
        Whether to escape the markdown characters as needed. This
        means that it does not escape extraneous characters if it's
        not necessary, e.g. ``**hello**`` is escaped into ``\*\*hello**``
        instead of ``\*\*hello\*\*``. Note however that this can open
        you up to some clever syntax abuse. Defaults to ``False``.
    ignore_links: :class:`bool`
        Whether to leave links alone when escaping markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. This option is not supported with ``as_needed``.
        Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters escaped with a slash.
    """

    if not as_needed:
        url_regex = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'
        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get('url')
            if is_url:
                return is_url
            return '\\' + groupdict['markdown']

        regex = r'(?P<markdown>[_\\~|\*`]|%s)' % _MARKDOWN_ESCAPE_COMMON
        if ignore_links:
            regex = '(?:%s|%s)' % (url_regex, regex)
        return re.sub(regex, replacement, text)
    else:
        text = re.sub(r'\\', r'\\\\', text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r'\\\1', text) 

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

    if (bot_user_id_reference in message_text):
      # this is a search request
      search_text = message_text.replace(bot_user_id_reference,"").strip()
      query_and_respond(say, search_text)
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

def query_and_respond(say, search_text = None, state = None, rerank = False, num_results = 1):
    """
    """
    filters = None
    search_filters = []
    if state != None:
      for block in state['values']:
        filters = state['values'][block]
        for filter in filters:
          if filter == 'filter_by_channel' and state['values'][block][filter]['selected_channel'] != None:
            search_filters.append('doc.channel = \'{}\''.format(state['values'][block][filter]['selected_channel']))
          elif filter == 'filter_by_user' and state['values'][block][filter]['selected_user'] != None:
            search_filters.append('doc.poster = \'{}\''.format(state['values'][block][filter]['selected_user']))
          elif filter == 'filter_start_date':
            utc_time = datetime.strptime(state['values'][block][filter]['selected_date'], "%Y-%m-%d")
            epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
            search_filters.append('doc.timestamp >= {}'.format(epoch_time))
          elif filter == 'filter_end_date':
            utc_time = datetime.strptime(state['values'][block][filter]['selected_date'], "%Y-%m-%d")
            epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
            search_filters.append('doc.timestamp <= {}'.format(epoch_time))
    search_query, search_results = search(search_text=search_text,
                                          rerank=rerank,
                                          num_results=num_results,
                                          metadata_filters=search_filters)
    
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
      if rerank == False and num_results == 1:
        blocks.append({
            "type": "divider"
        })
        blocks.append({
          "type": "actions",
          "elements": [
            {
              "type": "button",
              "text": {
                "type": "plain_text",
                "text": "Enable Reranker",
                "emoji": True
              },
              "value": json.dumps(search_query),
              "action_id": "enable_reranker"
            },
            {
              "type": "button",
              "text": {
                "type": "plain_text",
                "text": "More Results",
                "emoji": True
              },
              "value": json.dumps(search_query),
              "action_id": "more_results"
             }
          ]
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
        if rerank == True:
          blocks.insert(0, {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "Search Results (Reranked)"
            }
          })
        if num_results != 1:
          blocks.insert(0, {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "Search Results (Result {})".format(num_results)
            }
          })
      say(blocks=blocks, text="@{} said:\n> {}\n\n at {}".format(poster,text,timestamp), unfurl_links=False, unfurl_media=False, metadata={"foo":"bar"})
    else:
      say("Sorry, I couldn't find any relevant results")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get('SLACK_APP_TOKEN'))
    handler.start()
