import base64

from oslo_config import cfg
from keystoneclient.auth.base import BaseAuthPlugin


class HTTPAuth(BaseAuthPlugin):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_headers(self, session, **kwargs):
        return {'Authorization': 'Basic %s' % base64.standard_b64encode("%s:%s" % (self.username, self.password))}

    @classmethod
    def get_options(cls):
        return [
            cfg.StrOpt('username', help='username for basic HTTP authentication'),
            cfg.StrOpt('password', help='passowrd for basic HTTP authentication')
        ]
