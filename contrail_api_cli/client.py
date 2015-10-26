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

    def _get_url(self, path):
        if path.is_absolute():
            return self.base_url + str(path)
        raise ValueError("Path must be absolute")

    def get(self, path, **kwargs):
        url = self._get_url(path)
        if path.is_collection:
            url += 's'
        r = self.SESSION.get(url, user_agent=self.USER_AGENT, params=kwargs)
        return r.json(object_hook=utils.decode_paths)

    def delete(self, path):
        self.SESSION.delete(self._get_url(path), user_agent=self.USER_AGENT)
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
                              headers=headers, user_agent=self.USER_AGENT)
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
