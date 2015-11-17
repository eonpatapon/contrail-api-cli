import json
from argparse import Namespace

from keystoneclient.auth import base
from keystoneclient.session import Session

from .utils import classproperty
from .resource import ResourceBase, ResourceEncoder


class ContrailAPISession(Session):
    user_agent = "contrail-api-cli"
    protocol = None
    host = None
    port = None
    session = None

    @classproperty
    def base_url(cls):
        return "%s://%s:%s" % (cls.protocol, cls.host, cls.port)

    @classproperty
    def make_url(cls, uri):
        return cls.base_url + uri

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

    def get(self, url, **kwargs):
        r = super(ContrailAPISession, self).get(url, params=kwargs)
        return r.json()

    def post(self, url, data):
        """
        POST data to the api-server

        @param url: resource location (eg: "/type/uuid")
        @type url: str
        @type data: dict
        @rtype: dict
        """
        headers = {"content-type": "application/json"}
        r = super(ContrailAPISession, self).post(url,
                                                 data=to_json(data),
                                                 headers=headers)
        return r.json()

    def put(self, url, data):
        """
        PUT data to the api-server

        @param url: resource location (eg: "/type/uuid")
        @type url: str
        @type data: dict
        @rtype: dict
        """
        headers = {"content-type": "application/json"}
        r = super(ContrailAPISession, self).put(url,
                                                data=to_json(data),
                                                headers=headers)
        return r.json()

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
            uuid = self.post("/fqname-to-id", data)['uuid']
            return uuid
        except:
            return None


def to_json(resource_dict, cls=ResourceEncoder):
    return json.dumps(resource_dict,
                      indent=2,
                      sort_keys=True,
                      skipkeys=True,
                      cls=cls)
