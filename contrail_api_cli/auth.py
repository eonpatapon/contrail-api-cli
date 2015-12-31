from __future__ import unicode_literals
import base64
from six import b

from oslo_config import cfg
from keystoneclient.auth.base import BaseAuthPlugin


class HTTPAuth(BaseAuthPlugin):

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

    def get_headers(self, session, **kwargs):
        if self.username is None and self.password is None:
            return {}
        auth = "%s:%s" % (self.username, self.password)
        return {'Authorization': 'Basic %s' % base64.b64encode(b(auth)).decode('utf-8')}

    @classmethod
    def get_options(cls):
        return [
            cfg.StrOpt('username', help='username for basic HTTP authentication'),
            cfg.StrOpt('password', help='password for basic HTTP authentication')
        ]
