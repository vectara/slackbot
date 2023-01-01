import re

def homepage_blocks():
    return ([
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Welcome to Vectara* :tada:"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "To interact with Vectara with this slackbot:\n1. Invite it to any channels you want to be searchable\n2. Wait :slightly_smiling_face:"
            }
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "The slackbot doesn't attempt to index any message history prior to it joining: it will only index Slack messages sent after the bot is in the channel"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "After messages have been sent while the bot has been in the channels, you can perform searches several ways:\n1. Send me a message: `@` me and then send query text e.g. `@VectaraSlackSearch who mentioned going to Hawaii?`\n2. Use the `/vectara` command, e.g. `/vectara who mentioned going to Hawaii?`\n3. Use the `/vectara` command with channel parameters, e.g. `/vectara #vacations who mentioned going to Hawaii` to limit the search to just that channel"
            }
          }
        ])

def escape_markdown(text, *, as_needed=False, ignore_links=True):
    """A helper function that escapes Discord's/Slack's markdown.

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

    # constants
    _MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c)
                                                for c in ('*', '`', '_', '~', '|'))
    _MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)'
    _MARKDOWN_ESCAPE_REGEX = re.compile(r'(?P<markdown>%s|%s)' % (_MARKDOWN_ESCAPE_SUBREGEX, _MARKDOWN_ESCAPE_COMMON))

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