"""Utility functions for generating Twitter OAuth headers and making API calls.
"""

import logging
import urllib2

import appengine_config
import handlers
import requests
import requests_oauthlib
import tweepy


def auth_header(url, token_key, token_secret, method='GET'):
  """Generates an Authorization header and returns it in a header dict.

  Args:
    url: string
    token_key: string
    token_secret: string
    method: string

  Returns: single element dict with key 'Authorization'
  """
  oauth1 = requests_oauthlib.OAuth1(
    client_key=appengine_config.TWITTER_APP_KEY,
    client_secret=appengine_config.TWITTER_APP_SECRET,
    resource_owner_key=token_key,
    resource_owner_secret=token_secret,
    )
  req = requests.Request(method=method, url=url, auth=oauth1).prepare()

  logging.debug(
    'Generated Authorization header from access token key %s... and secret %s...',
    token_key[:4], token_secret[:4])
  return req.headers


def signed_urlopen(url, token_key, token_secret, headers=None, **kwargs):
  """Wraps urllib2.urlopen() and adds an OAuth signature.
  """
  if headers is None:
    headers = {}

  # if this is a post, move the body params into the URL. Tweepy's OAuth
  # signing doesn't work if they're in the body; Twitter returns a 401.
  data = kwargs.get('data')
  if data:
    method = 'POST'
    url += ('&' if '?' in url else '?') + data
    kwargs['data'] = ''
  else:
    method = 'GET'

  headers.update(auth_header(url, token_key, token_secret, method=method))
  timeout = kwargs.pop('timeout', appengine_config.HTTP_TIMEOUT)
  logging.debug('Fetching %s', url)
  try:
    return urllib2.urlopen(urllib2.Request(url, headers=headers, **kwargs),
                           timeout=timeout)
  except BaseException, e:
    handlers.interpret_http_exception(e)
    raise


def tweepy_auth(token_key, token_secret):
  """Returns a tweepy.OAuthHandler.
  """
  assert (appengine_config.TWITTER_APP_KEY and
          appengine_config.TWITTER_APP_SECRET), (
    "Please fill in the twitter_app_key and twitter_app_secret files in "
    "your app's root directory.")
  handler = tweepy.OAuthHandler(appengine_config.TWITTER_APP_KEY,
                                appengine_config.TWITTER_APP_SECRET)
  handler.set_access_token(token_key, token_secret)
  return handler

