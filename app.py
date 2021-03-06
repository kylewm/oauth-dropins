"""Example oauth-dropins app. Serves the front page and discovery files.
"""

import appengine_config

import blogger_v2
import disqus
import dropbox
import facebook
import flickr
import googleplus
import instagram
import tumblr
import twitter
import wordpress_rest

from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
import webapp2


class FrontPageHandler(webapp2.RequestHandler):
  """Renders and serves /, ie the front page.
  """
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'

    vars = dict(self.request.params)
    key = vars.get('auth_entity')
    if key:
      vars['entity'] = ndb.Key(urlsafe=key).get()

    self.response.out.write(template.render('templates/index.html', vars))


application = webapp2.WSGIApplication([
    ('/', FrontPageHandler),
    ('/blogger_v2/start', blogger_v2.StartHandler.to('/blogger_v2/oauth_callback')),
    ('/blogger_v2/oauth_callback', blogger_v2.CallbackHandler.to('/')),
    ('/disqus/start', disqus.StartHandler.to('/disqus/oauth_callback')),
    ('/disqus/oauth_callback', disqus.CallbackHandler.to('/')),
    ('/dropbox/start', dropbox.StartHandler.to('/dropbox/oauth_callback')),
    ('/dropbox/oauth_callback', dropbox.CallbackHandler.to('/')),
    ('/facebook/start', facebook.StartHandler.to('/facebook/oauth_callback')),
    ('/facebook/oauth_callback', facebook.CallbackHandler.to('/')),
    ('/flickr/start', flickr.StartHandler.to('/flickr/oauth_callback')),
    ('/flickr/oauth_callback', flickr.CallbackHandler.to('/')),
    ('/googleplus/start', googleplus.StartHandler.to('/googleplus/oauth_callback')),
    ('/googleplus/oauth_callback', googleplus.CallbackHandler.to('/')),
    ('/instagram/start', instagram.StartHandler.to('/instagram/oauth_callback')),
    ('/instagram/oauth_callback', instagram.CallbackHandler.to('/')),
    ('/tumblr/start', tumblr.StartHandler.to('/tumblr/oauth_callback')),
    ('/tumblr/oauth_callback', tumblr.CallbackHandler.to('/')),
    ('/twitter/start', twitter.StartHandler.to('/twitter/oauth_callback')),
    ('/twitter/oauth_callback', twitter.CallbackHandler.to('/')),
    ('/wordpress_rest/start', wordpress_rest.StartHandler.to(
        '/wordpress_rest/oauth_callback')),
    ('/wordpress_rest/oauth_callback', wordpress_rest.CallbackHandler.to('/')),
    ], debug=appengine_config.DEBUG)
