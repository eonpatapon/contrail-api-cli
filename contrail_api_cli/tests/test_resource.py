from __future__ import unicode_literals
import unittest
import json
try:
    import mock
except ImportError:
    import unittest.mock as mock

from keystoneclient.exceptions import HttpError

from contrail_api_cli.utils import Path, FQName
from contrail_api_cli.resource import RootCollection, Collection, Resource, ResourceEncoder
from contrail_api_cli.client import ContrailAPISession
from contrail_api_cli.exceptions import ResourceNotFound, ResourceMissing


BASE = "http://localhost:8082"


class TestResource(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_base(self, mock_session):
        mock_session.configure_mock(base_url=BASE)

        c = RootCollection()
        self.assertEqual(c.uuid, '')
        self.assertEqual(c.fq_name, FQName())
        self.assertEqual(c.href, BASE + '/')

        c = Collection('foo')
        self.assertEqual(c.uuid, '')
        self.assertEqual(c.fq_name, FQName())
        self.assertEqual(c.href, BASE + '/foos')

        r = Resource('foo', uuid='x')
        self.assertEqual(r.uuid, 'x')
        self.assertEqual(r.fq_name, FQName())
        self.assertEqual(r.href, BASE + '/foo/x')

        r = Resource('foo', fq_name='foo:bar')
        self.assertEqual(r.uuid, '')
        self.assertEqual(r.fq_name, FQName('foo:bar'))
        self.assertEqual(r.href, BASE + '/foos')

        r = Resource('foo', to='foo:bar')
        self.assertEqual(r.uuid, '')
        self.assertEqual(r.fq_name, FQName('foo:bar'))
        self.assertEqual(r.href, BASE + '/foos')

        with self.assertRaises(AssertionError):
            r = Resource('bar')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_root_collection(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        mock_session.get_json.return_value = {
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
        mock_session.get_json.return_value = {
            "instance-ips": [
                {"href": BASE + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                 "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"},
                {"href": BASE + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                 "uuid": "c2588045-d6fb-4f37-9f46-9451f653fb6a"}
            ]
        }

        collection = Collection('instance-ip', fetch=True)

        self.assertTrue(collection.href.endswith('s'))
        self.assertEqual(collection.fq_name, FQName())

        expected_collection = Collection('instance-ip', path=Path("/instance-ip"))
        expected_collection.data = [
            Resource(
                'instance-ip',
                href=BASE + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                uuid="ec1afeaa-8930-43b0-a60a-939f23a50724"
            ),
            Resource(
                'instance-ip',
                href=BASE + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                uuid="c2588045-d6fb-4f37-9f46-9451f653fb6a"
            )
        ]
        self.assertEqual(collection, expected_collection)

    # FIXME failed either with python2 or with python3 because
    # of unicode_literals
    # @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    # def test_resource_str(self, mock_session):
        # r = Resource('foo', key='foo', key2='bar')
        # self.assertTrue(str(r) in (str({'key': 'foo', 'key2': 'bar'}),
        # str({'key2': 'bar', 'key': 'foo'})))

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_fqname(self, mock_session):
        r = Resource('foo', fq_name=['domain', 'foo', 'uuid'])
        self.assertEqual(str(r.fq_name), 'domain:foo:uuid')
        r = Resource('foo', to=['domain', 'foo', 'uuid'])
        self.assertEqual(str(r.fq_name), 'domain:foo:uuid')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource(self, mock_session):
        # bind original method to mock_session
        mock_session.make_url = ContrailAPISession.make_url.__get__(mock_session)
        mock_session.get_json.return_value = {
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
                        "href": BASE + "/bar/15315402-8a21-4116-aeaa-b6a77dceb191",
                        "uuid": "15315402-8a21-4116-aeaa-b6a77dceb191",
                        "to": [
                            "bar",
                            "15315402-8a21-4116-aeaa-b6a77dceb191"
                        ]
                    }
                ]
            }
        }
        resource = Resource("foo", uuid="ec1afeaa-8930-43b0-a60a-939f23a50724", fetch=True)

        expected_resource = Resource(
            "foo",
            uuid="ec1afeaa-8930-43b0-a60a-939f23a50724",
            href=BASE + "/foo/ec1afeaa-8930-43b0-a60a-939f23a50724",
            attr=None,
            fq_name=["foo", "ec1afeaa-8930-43b0-a60a-939f23a50724"],
            bar_refs=[Resource("bar",
                               uuid="15315402-8a21-4116-aeaa-b6a77dceb191",
                               href=BASE + "/bar/15315402-8a21-4116-aeaa-b6a77dceb191",
                               to=["bar", "15315402-8a21-4116-aeaa-b6a77dceb191"])]
        )
        self.assertEqual(resource, expected_resource)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_fqname_validation(self, mock_session):
        # bind original method to mock_session
        mock_session.fqname_to_id = ContrailAPISession.fqname_to_id.__get__(mock_session)
        mock_session.post_json = ContrailAPISession.post_json.__get__(mock_session)
        mock_session.make_url = ContrailAPISession.make_url.__get__(mock_session)

        # called by fqname_to_id
        def post(url, data=None, headers=None):
            data = json.loads(data)
            result = mock.Mock()
            if data['type'] == "foo":
                result.json.return_value = {
                    "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"
                }
                return result
            if data['type'] == "bar":
                raise HttpError()

        mock_session.post.side_effect = post
        r = Resource('foo', fq_name='domain:foo:uuid', check=True)
        self.assertEqual(r.uuid, 'ec1afeaa-8930-43b0-a60a-939f23a50724')
        self.assertEqual(r.path, Path('/foo/ec1afeaa-8930-43b0-a60a-939f23a50724'))

        with self.assertRaises(ResourceNotFound) as e:
            r = Resource('bar', fq_name='domain:bar:nofound', check=True)
            self.assertEqual(str(e), "Resource domain:bar:nofound doesn't exists")

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_uuid_validation(self, mock_session):
        # bind original method to mock_session
        mock_session.id_to_fqname = ContrailAPISession.id_to_fqname.__get__(mock_session)
        mock_session.make_url = ContrailAPISession.make_url.__get__(mock_session)

        # called by id_to_fqname
        def post(url, json):
            if json['uuid'] == 'a5a1b67b-4246-4e2d-aa24-479d8d47435d':
                return {
                    'fq_name': [
                        'domain',
                        'foo',
                        'uuid'
                    ]
                }
            else:
                raise HttpError()

        mock_session.post_json.side_effect = post
        r = Resource('foo', uuid='a5a1b67b-4246-4e2d-aa24-479d8d47435d', check=True)
        self.assertEqual(str(r.fq_name), 'domain:foo:uuid')
        self.assertEqual(r.path, Path('/foo/a5a1b67b-4246-4e2d-aa24-479d8d47435d'))
        with self.assertRaises(ResourceNotFound) as e:
            r = Resource('bar', uuid='d6e9fae3-628c-448c-bfc5-849d82a9a016', check=True)
            self.assertEqual(str(e), "Resource d6e9fae3-628c-448c-bfc5-849d82a9a016 doesn't exists")

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_fetch(self, mock_session):
        mock_session.configure_mock(base_url=BASE)

        mock_session.fqname_to_id.side_effect = HttpError()
        r = Resource('foo', fq_name='domain:bar:foo')
        with self.assertRaises(ResourceNotFound):
            r.fetch()

        mock_session.fqname_to_id.side_effect = [
            "07eeb3c0-42f5-427c-9409-6ae45b376aa2"
        ]
        r = Resource('foo', fq_name='domain:bar:foo')
        r.fetch()
        self.assertEqual(r.uuid, '07eeb3c0-42f5-427c-9409-6ae45b376aa2')
        mock_session.get_json.assert_called_with(r.href)

        r.fetch(exclude_children=True)
        mock_session.get_json.assert_called_with(r.href, exclude_children=True)

        r.fetch(exclude_back_refs=True)
        mock_session.get_json.assert_called_with(r.href, exclude_back_refs=True)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_save(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        mock_session.post_json.return_value = {
            'foo': {
                'uuid': '8240f9c7-0f28-4ca7-b92e-2f6441a0a6dd'
            }
        }
        r = Resource('foo', fq_name='domain:bar:foo')
        r['foo'] = 'bar'
        r.save()
        mock_session.post_json.assert_called_with(BASE + '/foos',
                                                  {'foo': {'foo': 'bar',
                                                           'fq_name': ['domain', 'bar', 'foo']}},
                                                  cls=ResourceEncoder)

        mock_session.put_json.return_value = {
            'foo': {
                'uuid': '8240f9c7-0f28-4ca7-b92e-2f6441a0a6dd'
            }
        }
        r = Resource('foo', uuid='4c7dc905-3322-49c8-be5d-d4adb5571d41')
        r['foo'] = 'bar'
        r.save()
        mock_session.put_json.assert_called_with(BASE + '/foo/4c7dc905-3322-49c8-be5d-d4adb5571d41',
                                                 {'foo': {
                                                     'foo': 'bar',
                                                     'uuid': '4c7dc905-3322-49c8-be5d-d4adb5571d41'
                                                 }},
                                                 cls=ResourceEncoder)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_parent(self, mock_session):
        mock_session.configure_mock(base_url=BASE)

        p = Resource('bar', uuid='57ef609c-6c9b-4b91-a542-26c61420c37b')
        r = Resource('foo', fq_name='domain:foo', parent=p)
        self.assertEqual(p, r.parent)

        mock_session.id_to_fqname.side_effect = HttpError()
        with self.assertRaises(ResourceNotFound):
            p = Resource('not-found', uuid='1fe29f52-28dc-44a5-90d0-43de1b02cbd8')
            Resource('foo', fq_name='domain:foo', parent=p)

        with self.assertRaises(ResourceMissing):
            r = Resource('foo', fq_name='domain:foo')
            r.parent

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_check(self, mock_session):
        mock_session.configure_mock(base_url=BASE)

        mock_session.id_to_fqname.side_effect = HttpError()
        r = Resource('bar', uuid='57ef609c-6c9b-4b91-a542-26c61420c37b')
        self.assertFalse(r.exists)

        mock_session.id_to_fqname.side_effect = [
            FQName('domain:bar')
        ]
        r = Resource('bar', uuid='57ef609c-6c9b-4b91-a542-26c61420c37b')
        self.assertTrue(r.exists)

        mock_session.fqname_to_id.side_effect = HttpError()
        r = Resource('bar', fq_name='domain:foo')
        self.assertFalse(r.exists)

        mock_session.fqname_to_id.side_effect = [
            '588e1a17-ae50-4b67-8078-95f061d833ca'
        ]
        self.assertTrue(r.exists)


class TestCollection(unittest.TestCase):

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_fields(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        c = Collection('foo', fields=['foo', 'bar'], fetch=True)
        mock_session.get_json.assert_called_with(BASE + '/foos', fields='foo,bar')
        c.fetch(fields=['baz'])
        mock_session.get_json.assert_called_with(BASE + '/foos', fields='foo,bar,baz')
        c.fetch()
        mock_session.get_json.assert_called_with(BASE + '/foos', fields='foo,bar')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_filters(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        c = Collection('foo', filters=[('foo', 'bar')], fetch=True)
        mock_session.get_json.assert_called_with(BASE + '/foos', filters='foo=="bar"')
        c.fetch(filters=[('bar', False)])
        mock_session.get_json.assert_called_with(BASE + '/foos', filters='foo=="bar",bar==false')
        c.fetch()
        mock_session.get_json.assert_called_with(BASE + '/foos', filters='foo=="bar"')
        c.filter('bar', 42)
        c.fetch()
        mock_session.get_json.assert_called_with(BASE + '/foos', filters='foo=="bar",bar==42')

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
        mock_session.get_json.assert_called_with(BASE + '/foos', parent_id=expected_parent_id)
        c.fetch(parent_uuid='a9420bd1-59dc-4576-a548-b28cedbf3e5c')
        expected_parent_id = '0d7d4197-891b-4767-b599-54667370cab1,3a0e179e-fbe6-4390-8e5d-00a630de0b68,a9420bd1-59dc-4576-a548-b28cedbf3e5c'
        mock_session.get_json.assert_called_with(BASE + '/foos', parent_id=expected_parent_id)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_count(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        mock_session.get_json.return_value = {
            "instance-ips": {
                "count": 2
            }
        }

        c = Collection('instance-ip')
        self.assertEqual(len(c), 2)
        expected_calls = [
            mock.call(BASE + '/instance-ips', count=True),
        ]
        self.assertEqual(mock_session.get_json.mock_calls, expected_calls)

        mock_session.get_json.return_value = {
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
        self.assertEqual(mock_session.get_json.mock_calls, expected_calls)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_collection_contrail_name(self, mock_session):
        c = Collection('')
        self.assertEqual(c._contrail_name, '')
        c = Collection('foo')
        self.assertEqual(c._contrail_name, 'foos')


if __name__ == "__main__":
    unittest.main()
