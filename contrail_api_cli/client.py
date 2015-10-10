import requests
from requests.exceptions import ConnectionError

from contrail_api_cli.utils import Path

BASE_URL = "http://localhost:8082"


class APIError(Exception):
    pass


class APIClient:

    def request(self, path):
        url = BASE_URL + str(path)
        if not path.is_resource and not path.is_root:
            url += 's'
        try:
            r = requests.get(url)
        except ConnectionError:
            raise APIError("Failed to connect to API server")
        if r.status_code == 200:
            return r.json()
        raise APIError(r.text)

    def list(self, path):
        data = self.request(path)
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
                resource_path = Path(str(path))
                resource_path.cd(resource["uuid"])
                resource_path.meta["fq_name"] = ":".join(resource.get("fq_name", []))
                resources.append(resource_path)
        return resources

    def _get_home_resources(self, path, data):
        resources = []
        for resource in data['links']:
            if resource["link"]["rel"] == "resource-base":
                resource_path = Path(str(path))
                resource_path.cd(resource["link"]["name"])
                resources.append(resource_path)
        return resources
