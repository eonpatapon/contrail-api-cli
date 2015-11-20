import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

from contrail_api_cli.utils import Path
from contrail_api_cli.resource import RootCollection, Collection, Resource


BASE = "http://localhost:8082"


class TestResource(unittest.TestCase):

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_root_collection(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        mock_session.get.return_value = {
            "href": BASE,
            "links": [
                {"link": {"href": BASE + "/instance-ips",
                          "path": Path("/instance-ips"),
                          "name": "instance-ip",
                          "rel": "collection"}},
                {"link": {"href": BASE + "/instance-ip",
                          "path": Path("/instance-ip"),
                          "name": "instance-ip",
                          "rel": "resource-base"}}
            ]
        }
        root_collection = RootCollection(fetch=True)

        self.assertFalse(root_collection.href.endswith('s'))

        expected_root_resources = RootCollection(path=Path("/"))
        expected_root_resources.data = [
            Collection(
                "instance-ip",
                href=BASE + "/instance-ips",
                path=Path("/instance-ip"),
                name="instance-ip",
                rel="collection"
            )
        ]
        self.assertEqual(root_collection, expected_root_resources)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_collection(self, mock_session):
        mock_session.get.return_value = {
            "instance-ips": [
                {"href": BASE + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                 "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"},
                {"href": BASE + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                 "uuid": "c2588045-d6fb-4f37-9f46-9451f653fb6a"}
            ]
        }

        collection = Collection('instance-ip', fetch=True)

        self.assertTrue(collection.href.endswith('s'))
        self.assertEqual(collection.fq_name, '')

        expected_collection = Collection('instance-ip', path=Path("/instance-ip"))
        expected_collection.data = [
            Resource(
                'instance-ip',
                href=BASE + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                path=Path("/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724"),
                uuid="ec1afeaa-8930-43b0-a60a-939f23a50724"
            ),
            Resource(
                'instance-ip',
                href=BASE + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                path=Path("/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a"),
                uuid="c2588045-d6fb-4f37-9f46-9451f653fb6a"
            )
        ]
        self.assertEqual(collection, expected_collection)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_count(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        mock_session.get.return_value = {
            "instance-ips": {
                "count": 2
            }
        }

        c = Collection('instance-ip')
        self.assertEqual(len(c), 2)
        expected_calls = [
            mock.call(BASE + '/instance-ips', count=True),
        ]
        self.assertEqual(mock_session.get.mock_calls, expected_calls)

        mock_session.get.return_value = {
            "instance-ips": [
                {"href": BASE + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                 "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"},
                {"href": BASE + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                 "uuid": "c2588045-d6fb-4f37-9f46-9451f653fb6a"}
            ]
        }
        c.fetch()
        self.assertEqual(len(c), 2)
        expected_calls.append(
            mock.call(BASE + '/instance-ips')
        )
        self.assertEqual(mock_session.get.mock_calls, expected_calls)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource(self, mock_session):
        mock_session.get.return_value = {
            "foo": {
                "href": BASE + "/foo/ec1afeaa-8930-43b0-a60a-939f23a50724",
                "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                "attr": None,
                "fq_name": [
                    "foo",
                    "ec1afeaa-8930-43b0-a60a-939f23a50724"
                ],
                "bar_refs": [
                    {
                        "href": BASE + "/bar/ec1afeaa-8930-43b0-a60a-939f23a50724",
                        "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                        "to": [
                            "bar",
                            "ec1afeaa-8930-43b0-a60a-939f23a50724"
                        ]
                    }
                ]
            }
        }
        resource = Resource("foo", uuid="ec1afeaa-8930-43b0-a60a-939f23a50724", fetch=True)

        expected_resource = Resource(
            "foo",
            uuid="ec1afeaa-8930-43b0-a60a-939f23a50724",
            path=Path('/foo/ec1afeaa-8930-43b0-a60a-939f23a50724'),
            href=BASE + "/foo/ec1afeaa-8930-43b0-a60a-939f23a50724",
            attr=None,
            fq_name=["foo", "ec1afeaa-8930-43b0-a60a-939f23a50724"],
            bar_refs=[Resource("bar",
                               uuid="ec1afeaa-8930-43b0-a60a-939f23a50724",
                               href=BASE + "/bar/ec1afeaa-8930-43b0-a60a-939f23a50724",
                               fq_name=["bar", "ec1afeaa-8930-43b0-a60a-939f23a50724"])]
        )

        self.assertEqual(resource, expected_resource)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_fields(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        c = Collection('foo', fields=['foo', 'bar'], fetch=True)
        mock_session.get.assert_called_with(BASE + '/foos', fields='foo,bar')
        c.fetch(fields=['baz'])
        mock_session.get.assert_called_with(BASE + '/foos', fields='foo,bar,baz')
        c.fetch()
        mock_session.get.assert_called_with(BASE + '/foos', fields='foo,bar')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_filters(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        c = Collection('foo', filters=[('foo', 'bar')], fetch=True)
        mock_session.get.assert_called_with(BASE + '/foos', filters='foo=="bar"')
        c.fetch(filters=[('bar', False)])
        mock_session.get.assert_called_with(BASE + '/foos', filters='foo=="bar",bar==false')
        c.fetch()
        mock_session.get.assert_called_with(BASE + '/foos', filters='foo=="bar"')
        c.filter('bar', 42)
        c.fetch()
        mock_session.get.assert_called_with(BASE + '/foos', filters='foo=="bar",bar==42')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_parent_uuid(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        c = Collection('foo', parent_uuid='aa')
        self.assertEqual(c.parent_uuid, [])
        c = Collection('foo', parent_uuid='0d7d4197-891b-4767-b599-54667370cab1')
        self.assertEqual(c.parent_uuid, ['0d7d4197-891b-4767-b599-54667370cab1'])
        c = Collection('foo', parent_uuid=['0d7d4197-891b-4767-b599-54667370cab1',
                                           '3a0e179e-fbe6-4390-8e5d-00a630de0b68'])
        self.assertEqual(c.parent_uuid, ['0d7d4197-891b-4767-b599-54667370cab1',
                                         '3a0e179e-fbe6-4390-8e5d-00a630de0b68'])
        c.fetch()
        expected_parent_id = '0d7d4197-891b-4767-b599-54667370cab1,3a0e179e-fbe6-4390-8e5d-00a630de0b68'
        mock_session.get.assert_called_with(BASE + '/foos', parent_id=expected_parent_id)
        c.fetch(parent_uuid='a9420bd1-59dc-4576-a548-b28cedbf3e5c')
        expected_parent_id = '0d7d4197-891b-4767-b599-54667370cab1,3a0e179e-fbe6-4390-8e5d-00a630de0b68,a9420bd1-59dc-4576-a548-b28cedbf3e5c'
        mock_session.get.assert_called_with(BASE + '/foos', parent_id=expected_parent_id)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_fqname(self, mock_session):
        fq_name = "default-domain:foo:b25f5a6b-292f-4d0c-b5c6-22ad7209abe5"
        uuid = "b25f5a6b-292f-4d0c-b5c6-22ad7209abe5"
        mock_session.fqname_to_id.return_value = uuid
        r = Resource('foo', fq_name=fq_name)
        mock_session.fqname_to_id.assert_called_with('foo', fq_name)
        self.assertEqual(r.uuid, uuid)
        self.assertEqual(r.path, Path("/foo/b25f5a6b-292f-4d0c-b5c6-22ad7209abe5"))

if __name__ == "__main__":
    unittest.main()
