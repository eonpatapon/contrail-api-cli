from __future__ import unicode_literals
import os
import platform
from argparse import Namespace
from functools import wraps
import requests

from keystoneauth1 import loading
from keystoneauth1.session import Session
from keystoneauth1.exceptions.http import HttpError

from .utils import FQName, to_json


def contrail_error_handler(f):
    """Handle HTTP errors returned by the API server
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HttpError as e:
            # Replace message by details to provide a
            # meaningful message
            if e.details:
                e.message, e.details = e.details, e.message
                e.args = ("%s (HTTP %s)" % (e.message, e.http_status),)
            raise
    return wrapper


class SessionLoader(loading.session.Session):

    @property
    def plugin_class(self):
        return ContrailAPISession

    def make(self, host="localhost", port=8082, protocol="http", os_auth_type="http", **kwargs):
        """Initialize a session to Contrail API server

        :param os_auth_type: auth plugin to use:
            - http: basic HTTP authentification
            - v2password: keystone v2 auth
            - v3password: keystone v3 auth
        :type os_auth_type: str
        """
        loader = loading.base.get_plugin_loader(os_auth_type)
        plugin_options = {opt.dest: kwargs.pop("os_%s" % opt.dest)
                          for opt in loader.get_options()
                          if 'os_%s' % opt.dest in kwargs}
        plugin = loader.load_from_options(**plugin_options)
        return self.load_from_argparse_arguments(Namespace(**kwargs),
                                                 host=host,
                                                 port=port,
                                                 protocol=protocol,
                                                 auth=plugin)

    def register_argparse_arguments(self, parser):
        contrail_group = parser.add_argument_group(
            'Contrail API Connection Options',
            'Options controlling the Contrail HTTP API Connections')

        contrail_group.add_argument('--host', '-H',
                                    default=os.environ.get('CONTRAIL_API_HOST', 'localhost'),
                                    type=str,
                                    help="host to connect to (default='%(default)s')")
        contrail_group.add_argument('--port', '-p',
                                    default=os.environ.get('CONTRAIL_API_PORT', 8082),
                                    type=int,
                                    help="port to connect to (default='%(default)s')")
        contrail_group.add_argument('--protocol',
                                    type=str,
                                    default=os.environ.get('CONTRAIL_API_PROTOCOL', 'http'),
                                    help="protocol used (default=%(default)s)")
        super(SessionLoader, self).register_argparse_arguments(parser)


def load_from_argparse_arguments(options):
    return SessionLoader().make(**vars(options))


def register_argparse_arguments(parser):
    return SessionLoader().register_argparse_arguments(parser)


class ContrailAPISession(Session):
    user_agent = "contrail-api-cli"
    protocol = None
    host = None
    port = None
    default_headers = {
        'X-Contrail-Useragent': '%s:%s' % (platform.node(), 'contrail-api-cli'),
        "Content-Type": "application/json"
    }

    def __init__(self, host="localhost", port=8082, protocol="http", **kwargs):
        self.host = host
        self.port = port
        self.protocol = protocol
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        super(ContrailAPISession, self).__init__(session=session, **kwargs)

    @property
    def user(self):
        if hasattr(self.auth, 'username'):
            return self.auth.username
        else:
            return 'unknown'

    @property
    def base_url(self):
        return "%s://%s:%s" % (self.protocol, self.host, self.port)

    def make_url(self, uri):
        return self.base_url + uri

    @contrail_error_handler
    def get_json(self, url, **kwargs):
        return self.get(url, params=kwargs).json()

    @contrail_error_handler
    def delete(self, *args, **kwargs):
        return super(ContrailAPISession, self).delete(*args, **kwargs)

    @contrail_error_handler
    def post_json(self, url, data, cls=None, **kwargs):
        """
        POST data to the api-server

        :param url: resource location (eg: "/type/uuid")
        :type url: str
        :param cls: JSONEncoder class
        :type cls: JSONEncoder
        """
        kwargs['data'] = to_json(data, cls=cls)
        kwargs['headers'] = self.default_headers
        return self.post(url, **kwargs).json()

    @contrail_error_handler
    def put_json(self, url, data, cls=None, **kwargs):
        """
        PUT data to the api-server

        :param url: resource location (eg: "/type/uuid")
        :type url: str
        :param cls: JSONEncoder class
        :type cls: JSONEncoder
        """
        kwargs['data'] = to_json(data, cls=cls)
        kwargs['headers'] = self.default_headers
        return self.put(url, **kwargs).json()

    def fqname_to_id(self, fq_name, type):
        """
        Return uuid for fq_name

        :param fq_name: resource fq name
        :type fq_name: FQName
        :param type: resource type
        :type type: str

        :rtype: UUIDv4 str
        :raises HttpError: fq_name not found
        """
        data = {
            "type": type,
            "fq_name": list(fq_name)
        }
        return self.post_json(self.make_url("/fqname-to-id"), data)["uuid"]

    def id_to_fqname(self, uuid, type=None):
        """
        Return fq_name and type for uuid

        If `type` is provided check that uuid is actually
        a resource of type `type`. Raise HttpError if it's
        not the case.

        :param uuid: resource uuid
        :type uuid: UUIDv4 str
        :param type: resource type
        :type type: str

        :rtype: dict {'type': str, 'fq_name': FQName}
        :raises HttpError: uuid not found
        """
        data = {
            "uuid": uuid
        }
        result = self.post_json(self.make_url("/id-to-fqname"), data)
        result['fq_name'] = FQName(result['fq_name'])
        if type is not None and not result['type'].replace('_', '-') == type:
            raise HttpError('uuid %s not found for type %s' % (uuid, type), http_status=404)
        return result

    def add_ref(self, r1, r2, attr=None):
        self._ref_update(r1, r2, 'ADD', attr)

    def remove_ref(self, r1, r2):
        self._ref_update(r1, r2, 'DELETE')

    def _ref_update(self, r1, r2, action, attr=None):
        data = {
            'type': r1.type,
            'uuid': r1.uuid,
            'ref-type': r2.type,
            'ref-uuid': r2.uuid,
            'ref-fq-name': list(r2.fq_name),
            'operation': action,
            'attr': attr
        }
        return self.post_json(self.make_url("/ref-update"), data)

    def search_kv_store(self, key):
        """Search for a key in the key-value store.
        :param key: string
        :rtype: string
        """
        data = {
            'operation': 'RETRIEVE',
            'key': key
        }
        return self.post_json(self.make_url("/useragent-kv"), data)['value']

    def get_kv_store(self):
        """Retrieve all key-value store elements.

        :rtype: [{key, value}] where key and value are strings.
        """
        data = {
            'operation': 'RETRIEVE',
            'key': None
        }
        return self.post_json(self.make_url("/useragent-kv"), data)['value']

    def add_kv_store(self, key, value):
        """Add a key-value store entry.

        :param key: string
        :param value: string
        """
        data = {
            'operation': 'STORE',
            'key': key,
            'value': value
        }
        return self.post(self.make_url("/useragent-kv"), data=to_json(data),
                         headers=self.default_headers).text

    def remove_kv_store(self, key):
        """Remove a key-value store entry.

        :param key: string
        """
        data = {
            'operation': 'DELETE',
            'key': key
        }
        return self.post(self.make_url("/useragent-kv"), data=to_json(data),
                         headers=self.default_headers).text
