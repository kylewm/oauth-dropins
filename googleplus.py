"""Google+ OAuth drop-in.

Google+ API docs: https://developers.google.com/+/api/latest/
Python API client docs: https://developers.google.com/api-client-library/python/

TODO: check that overriding CallbackHandler.finish() actually works.
"""

import json
import httplib2
import logging

import appengine_config
import handlers
import models

from apiclient import discovery
from apiclient.errors import HttpError
from oauth2client.appengine import CredentialsModel, OAuth2Decorator
from oauth2client.client import OAuth2Credentials
from google.appengine.ext import db
from google.appengine.ext import ndb
from webutil import handlers as webutil_handlers


# suppress "execute() takes at most 1 positional argument (2 given)"
# log warnings from google-api-python-client/oauth2client/util.py:124
import oauth2client
oauth2client.util.positional_parameters_enforcement = \
    oauth2client.util.POSITIONAL_IGNORE

# global
json_service = None

def init_json_service():
  global json_service
  if json_service is None:
    # service names and versions:
    # https://developers.google.com/api-client-library/python/apis/
    json_service = discovery.build('plus', 'v1')

# global. initialized in StartHandler.to_path().
oauth_decorator = None


class GooglePlusAuth(models.BaseAuth):
  """An authenticated Google+ user or page.

  Provides methods that return information about this user (or page) and make
  OAuth-signed requests to the Google+ API. Stores OAuth credentials in the
  datastore. See models.BaseAuth for usage details.

  Google+-specific details: implements http() and api() but not urlopen(). api()
  returns a apiclient.discovery.Resource. The datastore entity key name is the
  Google+ user id. Uses credentials from the stored CredentialsModel since
  google-api-python-client stores refresh tokens there.
  """
  user_json = ndb.TextProperty()
  creds_model = ndb.KeyProperty(kind='CredentialsModel')

  # deprecated. TODO: remove
  creds_json = ndb.TextProperty()

  def site_name(self):
    return 'Google+'

  def user_display_name(self):
    """Returns the user's name.
    """
    return json.loads(self.user_json)['displayName']

  def creds(self):
    """Returns an oauth2client.OAuth2Credentials.
    """
    if self.creds_model:
      return db.get(self.creds_model.to_old_key()).credentials
    else:
      # TODO: remove creds_json
      return OAuth2Credentials.from_json(self.creds_json)

  def access_token(self):
    """Returns the OAuth access token string.
    """
    return self.creds().access_token

  def http(self, **kwargs):
    """Returns an httplib2.Http that adds OAuth credentials to requests.
    """
    http = httplib2.Http(**kwargs)
    self.creds().authorize(http)
    return http

  def api(self):
    """Returns an apiclient.discovery.Resource for the Google+ JSON API.

    To use it, first choose a resource type (e.g. People), then make a call,
    then execute that call with an authorized Http instance. For example:

    gpa = GooglePlusAuth.get_by_id('123')
    results_json = gpa.people().search(query='ryan').execute(gpa.http())

    More details: https://developers.google.com/api-client-library/python/
    """
    init_json_service()
    return json_service


def handle_exception(self, e, debug):
  """Exception handler that passes back HttpErrors as real HTTP errors.
  """
  if isinstance(e, HttpError):
    logging.exception(e)
    self.response.set_status(e.resp.status)
    self.response.write(str(e))
  else:
    return webutil_handlers.handle_exception(self, e, debug)


class StartHandler(handlers.StartHandler, handlers.CallbackHandler):
  """Starts and finishes the OAuth flow. The decorator handles the redirects.
  """
  handle_exception = handle_exception

  # G+ scopes: https://developers.google.com/+/api/oauth#oauth-scopes
  DEFAULT_SCOPE = 'https://www.googleapis.com/auth/plus.me'

  @classmethod
  def to(cls, to_path, scopes=None):
    """Override this since we need to_path to instantiate the oauth decorator.
    """
    global oauth_decorator
    if oauth_decorator is None:
      oauth_decorator = OAuth2Decorator(
        client_id=appengine_config.GOOGLE_CLIENT_ID,
        client_secret=appengine_config.GOOGLE_CLIENT_SECRET,
        scope=cls.make_scope_str(scopes),
        callback_path=to_path,
        # make sure we ask for a refresh token so we can use it to get an access
        # token offline. requires approval_prompt=force! more:
        # ~/etc/google+_oauth_credentials_debugging_for_plusstreamfeed_bridgy
        # http://googleappsdeveloper.blogspot.com.au/2011/10/upcoming-changes-to-oauth-20-endpoint.html
        access_type='offline',
        approval_prompt='force',
        # https://developers.google.com/accounts/docs/OAuth2WebServer#incrementalAuth
        include_granted_scopes='true')

    class Handler(cls):
      @oauth_decorator.oauth_required
      def get(self):
        assert (appengine_config.GOOGLE_CLIENT_ID and
                appengine_config.GOOGLE_CLIENT_SECRET), (
          "Please fill in the google_client_id and google_client_secret files in "
          "your app's root directory.")

        # get the current user
        init_json_service()
        try:
          user = json_service.people().get(userId='me')\
              .execute(oauth_decorator.http())
        except BaseException, e:
          handlers.interpret_http_exception(e)
          raise
        logging.debug('Got one person: %r', user)

        store = oauth_decorator.credentials.store
        creds_model_key = ndb.Key(store._model.kind(), store._key_name)
        auth = GooglePlusAuth(id=user['id'],
                              creds_model=creds_model_key,
                              user_json=json.dumps(user))
        auth.put()
        self.finish(auth, state=self.request.get('state'))

      @oauth_decorator.oauth_required
      def post(self):
        return self.get()

    return Handler


class CallbackHandler(object):
  """OAuth callback handler factory.
  """
  @staticmethod
  def to(to_path):
    StartHandler.to_path = to_path
    global oauth_decorator
    assert oauth_decorator
    return oauth_decorator.callback_handler()
