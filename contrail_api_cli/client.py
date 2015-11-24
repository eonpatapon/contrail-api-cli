import json
from argparse import Namespace

from keystoneclient.auth import base
from keystoneclient.session import Session
from keystoneclient.exceptions import HTTPError

from .utils import classproperty
from .resource import ResourceBase, ResourceEncoder, ResourceWithoutPathEncoder


class ContrailAPISession(Session):
    user_agent = "contrail-api-cli"
    protocol = None
    host = None
    port = None
    session = None

    @classproperty
    def base_url(cls):
        return "%s://%s:%s" % (cls.protocol, cls.host, cls.port)

    def make_url(self, uri):
        return self.base_url + uri

    @classproperty
    def user(cls):
        return cls.session.auth.username

    @classmethod
    def make(cls, plugin_name, protocol="http", host="localhost", port=8082, **kwargs):
        """Initialize a session to Contrail API server

        @param plugin_name: auth plugin to use:
            - http: basic HTTP authentification
            - v2password: keystone v2 auth
            - v3password: keystone v3 auth
        @type plugin_name: str

        @param protocol: protocol used to connect to the API server (default: http)
        @type protocol: str
        @param host: API server host (default: localhost)
        @type host: str
        @param port: API server port (default: 8082)
        @type port: int

        @param kwargs: plugin arguments
        """
        cls.protocol = protocol
        cls.host = host
        cls.port = port
        plugin_cls = base.get_plugin_class(plugin_name)
        plugin_options = {opt.dest: kwargs.pop("os_%s" % opt.dest)
                          for opt in plugin_cls.get_options()}
        plugin = plugin_cls.load_from_options(**plugin_options)
        args = Namespace(**kwargs)
        session = cls.load_from_cli_options(args,
                                            auth=plugin)
        ResourceBase.session = session
        cls.session = session
        return session

    def get_json(self, url, **kwargs):
        return self.get(url, params=kwargs).json()

    def post(self, url, cls=ResourceWithoutPathEncoder, **kwargs):
        """
        POST data to the api-server

        @param url: resource location (eg: "/type/uuid")
        @type url: str
        @param cls: JSONEncoder class
        @type cls: JSONEncoder
        """
        if 'data' in kwargs:
            kwargs['data'] = to_json(kwargs['data'], cls=cls)
            kwargs['headers'].update({"content-type": "application/json"})
        return super(ContrailAPISession, self).post(url, **kwargs)

    def post_json(self, *args, **kwargs):
        return self.post(*args, **kwargs).json()

    def put(self, url, cls=ResourceWithoutPathEncoder, **kwargs):
        """
        PUT data to the api-server

        @param url: resource location (eg: "/type/uuid")
        @type url: str
        @param cls: JSONEncoder class
        @type cls: JSONEncoder
        """
        if 'data' in kwargs:
            kwargs['data'] = to_json(kwargs['data'], cls=cls)
            kwargs['headers'].update({"content-type": "application/json"})
        return super(ContrailAPISession, self).put(url, **kwargs)

    def put_json(self, *args, **kwargs):
        return self.put(*args, **kwargs).json()

    def fqname_to_id(self, type, fq_name):
        """
        Return uuid for fq_name

        @param type: resource type
        @type type: str
        @param fq_name: resource fq name (domain:project:identifier)
        @type fq_name: str

        @rtype: UUIDv4 str
        """
        data = {
            "type": type,
            "fq_name": fq_name.split(":")
        }
        try:
            return self.post_json(self.make_url("/fqname-to-id"), json=data)["uuid"]
        except HTTPError:
            return None

    def id_to_fqname(self, type, uuid):
        """
        Return fq_name for uuid

        @param type: resource type
        @type type: str
        @param uuid: resource uuid
        @type uuid: UUIDv4 str

        @rtype: str (domain:project:identifier)
        """
        data = {
            "type": type,
            "uuid": uuid
        }
        try:
            fq_name = self.post_json(self.make_url("/id-to-fqname"), json=data)['fq_name']
            return ":".join(fq_name)
        except HTTPError:
            return None


def to_json(resource_dict, cls=ResourceEncoder):
    return json.dumps(resource_dict,
                      indent=2,
                      sort_keys=True,
                      skipkeys=True,
                      cls=cls)
