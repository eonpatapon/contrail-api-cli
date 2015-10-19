import requests
from requests.exceptions import ConnectionError

from contrail_api_cli.utils import Path, classproperty


class APIError(Exception):
    pass


class APIClient:
    PROTOCOL = "http"
    HOST = "localhost:8082"
    USER = ""
    PASSWORD = ""

    @classproperty
    def base_url(cls):
        return cls.PROTOCOL + "://" + cls.HOST

    @property
    def _auth_token(self):
        if self.USER and self.PASSWORD:
            return (self.USER, self.PASSWORD)

    def get(self, path, **kwargs):
        url = APIClient.base_url + str(path)
        if not path.is_resource and not path.is_root:
            url += 's'
        try:
            r = requests.get(url, auth=self._auth_token, params=kwargs)
        except ConnectionError:
            raise APIError("Failed to connect to API server at %s" % APIClient.base_url)
        if r.status_code == 200:
            return r.json(object_hook=self._decode_paths)
        raise APIError(r.text)

    def delete(self, path):
        url = APIClient.base_url + str(path)
        r = requests.delete(url)
        if r.status_code == 200:
            return True
        raise APIError(r.text)

    def _decode_paths(self, obj):
        for attr, value in obj.items():
            if attr in ('href', 'parent_href'):
                obj[attr] = Path(value[len(self.base_url):])
                obj[attr].meta["fq_name"] = ":".join(obj.get('to', obj.get('fq_name', '')))
        return obj

    def list(self, path):
        data = self.get(path)
        if path.is_root:
            return self._get_home_resources(path, data)
        elif not path.is_resource:
            return self._get_resources(path, data)
        elif path.is_resource:
            return data[path.resource_name]

    def _get_resources(self, path, data):
        resources = []
        for resource_name, resource_list in data.items():
            for resource in resource_list:
                resources.append(resource["href"])
        return resources

    def _get_home_resources(self, path, data):
        resources = []
        for resource in data['links']:
            if resource["link"]["rel"] == "resource-base":
                resources.append(resource["link"]["href"])
        return resources
