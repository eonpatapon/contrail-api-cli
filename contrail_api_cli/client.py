import requests
from requests.exceptions import ConnectionError

from contrail_api_cli import utils


class APIError(Exception):
    pass


class APIClient:
    PROTOCOL = "http"
    HOST = "localhost:8082"
    USER = ""
    PASSWORD = ""

    @utils.classproperty
    def base_url(cls):
        return cls.PROTOCOL + "://" + cls.HOST

    @property
    def _auth_token(self):
        if self.USER and self.PASSWORD:
            return (self.USER, self.PASSWORD)

    def get(self, path, **kwargs):
        url = path.url
        if path.is_collection:
            url += 's'
        try:
            r = requests.get(url, auth=self._auth_token, params=kwargs)
        except ConnectionError:
            raise APIError("Failed to connect to API server at %s" % APIClient.base_url)
        if r.status_code == 200:
            return r.json(object_hook=utils.decode_paths)
        raise APIError(r.text)

    def delete(self, path):
        r = requests.delete(path.url)
        if r.status_code == 200:
            return True
        raise APIError(r.text)

    def post(self, path, data):
        """
        POST data to the api-server

        @type path: Path
        @type data: dict
        @rtype: dict
        """
        headers = {"content-type": "application/json"}
        r = requests.post(path.url, data=utils.to_json(data), headers=headers)
        if r.status_code == 200:
            return r.json(object_hook=utils.decode_paths)
        raise APIError(r.text)

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
        uuid = self.post(utils.Path("fqname-to-id"), data)['uuid']
        return utils.Path(path, uuid)

    def list(self, path):
        data = self.get(path)
        if path.is_root:
            return self._get_home_resources(data)
        elif path.is_collection:
            return self._get_resources(data)
        elif path.is_resource:
            return data[path.resource_name]

    def _get_resources(self, data):
        resources = []
        for resource_name, resource_list in data.items():
            for resource in resource_list:
                resources.append(resource["href"])
        return resources

    def _get_home_resources(self, data):
        resources = []
        for resource in data['links']:
            if resource["link"]["rel"] == "resource-base":
                resources.append(resource["link"]["href"])
        return resources
