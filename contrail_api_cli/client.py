from argparse import Namespace

from keystoneclient.auth import base
from keystoneclient.session import Session

from contrail_api_cli import utils


class APIClient:
    USER_AGENT = "contrail-api-cli"
    PROTOCOL = "http"
    HOST = "localhost:8082"
    SESSION = None

    @utils.classproperty
    def base_url(cls):
        return cls.PROTOCOL + "://" + cls.HOST

    @utils.classproperty
    def user(cls):
        return cls.SESSION.auth.username

    @classmethod
    def make_session(cls, plugin_name, **kwargs):
        plugin_cls = base.get_plugin_class(plugin_name)
        plugin_options = {opt.dest: kwargs.pop("os_%s" % opt.dest)
                          for opt in plugin_cls.get_options()}
        plugin = plugin_cls.load_from_options(**plugin_options)
        args = Namespace(**kwargs)
        cls.SESSION = Session.load_from_cli_options(args,
                                                    auth=plugin,
                                                    user_agent=cls.USER_AGENT)

    def _get_url(self, path):
        if path.is_absolute():
            return self.base_url + str(path)
        raise ValueError("Path must be absolute")

    def get(self, path, **kwargs):
        url = self._get_url(path)
        if path.is_collection:
            url += 's'
        r = self.SESSION.get(url, params=kwargs)
        return r.json(object_hook=utils.decode_paths)

    def delete(self, path):
        self.SESSION.delete(self._get_url(path))
        return True

    def post(self, path, data):
        """
        POST data to the api-server

        @type path: Path
        @type data: dict
        @rtype: dict
        """
        headers = {"content-type": "application/json"}
        r = self.SESSION.post(self._get_url(path), data=utils.to_json(data),
                              headers=headers)
        return r.json(object_hook=utils.decode_paths)

    def fqname_to_id(self, path, fq_name):
        """
        Return Path for fq_name

        @type path: Path
        @type fq_name: str
        @rtype: Path
        """
        data = {
            "type": path.resource_name,
            "fq_name": fq_name.split(":")
        }
        uuid = self.post(utils.Path("/fqname-to-id"), data)['uuid']
        return utils.Path(path, uuid)
