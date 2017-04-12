from __future__ import unicode_literals
import base64
from six import b

from keystoneauth1.plugin import BaseAuthPlugin
from keystoneauth1.loading import Opt, base


class HTTPAuthLoader(base.BaseLoader):

    @property
    def plugin_class(self):
        return HTTPAuth

    def get_options(self):
        return [
            Opt('username', help='username for basic HTTP authentication'),
            Opt('password', help='password for basic HTTP authentication')
        ]


class HTTPAuth(BaseAuthPlugin):

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

    def get_headers(self, session, **kwargs):
        if self.username is None and self.password is None:
            return {}
        auth = "%s:%s" % (self.username, self.password)
        return {'Authorization': 'Basic %s' % base64.b64encode(b(auth)).decode('utf-8')}
