from __future__ import unicode_literals
import json
import string
import re
from uuid import UUID
from six import string_types, text_type
from functools import wraps
from datetime import datetime
import itertools
import logging
try:
    from UserDict import UserDict
    from UserList import UserList
except ImportError:
    from collections import UserDict, UserList

import datrie
from keystoneauth1.exceptions.http import HttpError
from prompt_toolkit.completion import Completion

from .utils import FQName, Path, Observable, to_json
from .exceptions import ResourceNotFound, ResourceMissing, \
    CollectionNotFound, ChildrenExists, BackRefsExists
from .context import Context


logger = logging.getLogger(__name__)


def http_error_handler(f):
    """Handle 404 errors returned by the API server
    """

    def hrefs_to_resources(hrefs):
        for href in hrefs.replace(',', '').split():
            type, uuid = href.split('/')[-2:]
            yield Resource(type, uuid=uuid)

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except HttpError as e:
            if e.http_status == 404:
                # remove previously created resource
                # from the cache
                self.emit('deleted', self)
                if isinstance(self, Resource):
                    raise ResourceNotFound(resource=self)
                elif isinstance(self, Collection):
                    raise CollectionNotFound(collection=self)
            elif e.http_status == 409:
                matches = re.match('^Children (.*) still exist$', e.message)
                if matches:
                    raise ChildrenExists(
                        resources=list(hrefs_to_resources(matches.group(1))))
                matches = re.match('^Back-References from (.*) still exist$', e.message)
                if matches:
                    raise BackRefsExists(
                        resources=list(hrefs_to_resources(matches.group(1))))
            raise
    return wrapper


class LinkType(object):
    BACK_REF = "back_refs"
    REF = "refs"
    CHILDREN = "children"


class LinkedResources(object):
    """Intermediate class to manage linked resources of a resource.

    Given the LinkType the class allows iteration of linked resources
    and provide access to linked resources types via direct attributes.

    Linked types are validated be the resource schema.

    >>> vmi = Resource('virtual-machine-interface',
                       uuid='61ceff9d-9993-4d30-a337-abb0102f9f92')
    >>> vmi.fetch()
    >>> vmi.refs
    LinkedResources(refs)
    >>> vmi.refs.virtual_network
    [Resource(/virtual-network/6dee5930-5ea3-4fa9-adfd-6d5b68c360b7)]
    >>> list(vmi.refs)
    [Resource(/security-group/3304f964-f75c-4a3b-9f91-5c89090346bf),
     Resource(/virtual-network/6dee5930-5ea3-4fa9-adfd-6d5b68c360b7),
     Resource(/routing-instance/e055dd4f-d7d9-4979-95ac-44a5c6269278)]
    """
    def __init__(self, link_type, resource):
        self.link_type = link_type
        self.resource = resource
        self.linked_types = getattr(self.resource.schema, self.link_type)

    def _type_to_attr(self, type):
        type = type.replace('-', '_')
        if self.link_type == LinkType.CHILDREN:
            return type + 's'
        else:
            return type + '_' + self.link_type

    def _attr_to_type(self, attr):
        if self.link_type == LinkType.CHILDREN:
            attr = attr[:-1]
        else:
            attr = attr.split('_' + self.link_type)[0]
        return attr.replace('_', '-')

    def __getattr__(self, type):
        if type.replace('_', '-') not in self.linked_types:
            return []
        return self.resource.get(self._type_to_attr(type), [])

    def __iter__(self):
        return itertools.chain(*[getattr(self, res_type)
                                 for res_type in self.linked_types])

    def __getitem__(self, key):
        return list(self.__iter__())[key]

    def __dir__(self):
        return sorted(set(dir(type(self)) + list(self.__dict__) +
                      [t.replace('-', '_') for t in self.linked_types]))

    def encode(self, data, recursive=1):
        for attr, _ in list(data.items()):
            type = self._attr_to_type(attr)
            if type in self.linked_types:
                for idx, res in enumerate(data[attr]):
                    data[attr][idx] = Resource(type,
                                               fetch=recursive - 1 > 0,
                                               recursive=recursive - 1,
                                               **res)
                if self.link_type == LinkType.CHILDREN:
                    data[attr] = Collection(type, parent_uuid=self.resource.uuid,
                                            data=data[attr])
                elif self.link_type == LinkType.BACK_REF:
                    data[attr] = Collection(type, back_refs_uuid=self.resource.uuid,
                                            data=data[attr])
        return data

    def __repr__(self):
        return '%s' % list(self.__iter__())


class ResourceEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, FQName):
            return obj._data
        if isinstance(obj, Resource):
            return obj.data
        if isinstance(obj, Collection):
            return obj.data
        return super(ResourceEncoder, self).default(obj)


class ResourceBase(Observable):

    def __init__(self, session=None):
        self._session = session

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.path)

    def __hash__(self):
        if self.uuid:
            ident = (self.type, self.uuid)
        else:
            ident = (self.type,)
        return hash(ident)

    @property
    def session(self):
        if self._session is not None:
            return self._session
        return Context().session

    @property
    def uuid(self):
        return ''

    @property
    def fq_name(self):
        return FQName()

    @property
    def path(self):
        """Return Path of the resource

        :rtype: Path
        """
        return Path("/") / self.type / self.uuid

    @property
    def href(self):
        """Return URL of the resource

        :rtype: str
        """
        url = self.session.base_url + str(self.path)
        if self.path.is_collection and not self.path.is_root:
            return url + 's'
        return url


class Collection(ResourceBase, UserList):
    """Class for interacting with an API collection

    >>> from contrail_api_cli.resource import Collection
    >>> c = Collection('virtual-network', fetch=True)
    >>> # iterate over the resources
    >>> for r in c:
    >>>     print(r.path)
    >>> # filter support
    >>> c.filter("router_external", False)
    >>> c.fetch()
    >>> assert all([r.get('router_external') for r in c]) == False

    :param type: name of the collection
    :type type: str
    :param fetch: immediately fetch collection from the server
    :type fetch: bool
    :param recursive: level of recursion
    :type recursive: int
    :param fields: list of field names to fetch
    :type fields: [str]
    :param filters: list of filters
    :type filters: [(name, value), ...]
    :param parent_uuid: filter by parent_uuid
    :type parent_uuid: v4UUID str or list of v4UUID str
    :param back_ref_uuid: filter by back_ref_uuid
    :type back_ref_uuid: v4UUID str or list of v4UUID str
    :param data: initial resources of the collection
    :type data: [Resource]
    """

    def __init__(self, type, fetch=False, recursive=1,
                 fields=None, detail=None, filters=None,
                 parent_uuid=None, back_refs_uuid=None,
                 data=None, session=None):
        super(Collection, self).__init__(session=session)
        UserList.__init__(self, initlist=data)
        self.type = type
        self.fields = fields or []
        self.filters = filters or []
        self.parent_uuid = list(self._sanitize_uuid(parent_uuid))
        self.back_refs_uuid = list(self._sanitize_uuid(back_refs_uuid))
        self.detail = detail
        if fetch:
            self.fetch(recursive=recursive)
        self.emit('created', self)

    @http_error_handler
    def __len__(self):
        """Return the number of items of the collection

        :rtype: int
        """
        if not self.data:
            params = self._format_fetch_params()
            res = self.session.get_json(self.href, count=True, **params)
            try:
                return res[self._contrail_name]['count']
            except KeyError:
                return 0
        return super(Collection, self).__len__()

    @property
    def _contrail_name(self):
        if self.type:
            return self.type + 's'
        return self.type

    def _sanitize_uuid(self, uuid):
        if uuid is None:
            raise StopIteration
        if isinstance(uuid, string_types):
            uuid = [uuid]
        for u in uuid:
            try:
                UUID(u, version=4)
            except ValueError:
                continue
            yield u

    def filter(self, field_name, field_value):
        """Add permanent filter on the collection

        :param field_name: name of the field to filter on
        :type field_name: str
        :param field_value: value to filter on

        :rtype: Collection
        """
        self.filters.append((field_name, field_value))
        return self

    def _format_fetch_params(self, fields=[], detail=False, filters=[],
                             parent_uuid=None, back_refs_uuid=None):
        params = {}
        detail = detail or self.detail
        fields_str = ",".join(self._fetch_fields(fields))
        filters_str = ",".join(['%s==%s' % (f, json.dumps(v))
                                for f, v in self._fetch_filters(filters)])
        parent_uuid_str = ",".join(self._fetch_parent_uuid(parent_uuid))
        back_refs_uuid_str = ",".join(self._fetch_back_refs_uuid(back_refs_uuid))
        if detail is True:
            params['detail'] = detail
        elif fields_str:
            params['fields'] = fields_str
        if filters_str:
            params['filters'] = filters_str
        if parent_uuid_str:
            params['parent_id'] = parent_uuid_str
        if back_refs_uuid_str:
            params['back_ref_id'] = back_refs_uuid_str

        return params

    def _fetch_parent_uuid(self, parent_uuid=None):
        return self.parent_uuid + list(self._sanitize_uuid(parent_uuid))

    def _fetch_back_refs_uuid(self, back_refs_uuid=None):
        return self.back_refs_uuid + list(self._sanitize_uuid(back_refs_uuid))

    def _fetch_filters(self, filters=None):
        return self.filters + (filters or [])

    def _fetch_fields(self, fields=None):
        return self.fields + (fields or [])

    @http_error_handler
    def fetch(self, recursive=1, fields=None, detail=None,
              filters=None, parent_uuid=None, back_refs_uuid=None):
        """
        Fetch collection from API server

        :param recursive: level of recursion
        :type recursive: int
        :param fields: fetch only listed fields.
                       contrail 3.0 required
        :type fields: [str]
        :param detail: fetch all fields
        :type detail: bool
        :param filters: list of filters
        :type filters: [(name, value), ...]
        :param parent_uuid: filter by parent_uuid
        :type parent_uuid: v4UUID str or list of v4UUID str
        :param back_refs_uuid: filter by back_refs_uuid
        :type back_refs_uuid: v4UUID str or list of v4UUID str

        :rtype: Collection
        """

        params = self._format_fetch_params(fields=fields, detail=detail, filters=filters,
                                           parent_uuid=parent_uuid, back_refs_uuid=back_refs_uuid)
        data = self.session.get_json(self.href, **params)

        if not self.type:
            self.data = [Collection(col["link"]["name"],
                                    fetch=recursive - 1 > 0,
                                    recursive=recursive - 1,
                                    fields=self._fetch_fields(fields),
                                    detail=detail or self.detail,
                                    filters=self._fetch_filters(filters),
                                    parent_uuid=self._fetch_parent_uuid(parent_uuid),
                                    back_refs_uuid=self._fetch_back_refs_uuid(back_refs_uuid))
                         for col in data['links']
                         if col["link"]["rel"] == "collection"]
        else:
            # when detail=False, res == {resource_attrs}
            # when detail=True, res == {'type': {resource_attrs}}
            self.data = [Resource(self.type,
                                  fetch=recursive - 1 > 0,
                                  recursive=recursive - 1,
                                  **res.get(self.type, res))
                         for res_type, res_list in data.items()
                         for res in res_list]

        return self


class RootCollection(Collection):

    def __init__(self, **kwargs):
        return super(RootCollection, self).__init__('', **kwargs)


class Resource(ResourceBase, UserDict):
    """Class for interacting with an API resource

    >>> from contrail_api_cli.resource import Resource
    >>> r = Resource('virtual-network',
                     uuid='4c45e89b-7780-4b78-8508-314fe04a7cbd',
                     fetch=True)
    >>> r['display_name'] = 'foo'
    >>> r.save()

    >>> p = Resource('project', fq_name='default-domain:admin')
    >>> r = Resource('virtual-network', fq_name='default-domain:admin:net1',
                     parent=p)
    >>> r.save()

    :param type: type of the resource
    :type type: str
    :param fetch: immediately fetch resource from the server
    :type fetch: bool
    :param uuid: uuid of the resource
    :type uuid: v4UUID str
    :param fq_name: fq name of the resource
    :type fq_name: str (domain:project:identifier)
                   or list ['domain', 'project', 'identifier']
    :param check: check that the resource exists
    :type check: bool
    :param parent: parent resource
    :type parent: Resource
    :param recursive: level of recursion
    :type recursive: int

    :raises ResourceNotFound: bad uuid or fq_name is given
    :raises HttpError: when save(), fetch() or delete() fail

    .. note::

        Either fq_name or uuid must be provided.
    """

    def __init__(self, type, fetch=False, check=False,
                 parent=None, recursive=1, session=None, **kwargs):
        assert('fq_name' in kwargs or 'uuid' in kwargs or 'to' in kwargs)
        super(Resource, self).__init__(session=session)
        self.type = type

        UserDict.__init__(self, kwargs)
        self.from_dict(self.data)

        if parent:
            self.parent = parent

        if check:
            self.check()

        if fetch:
            self.fetch(recursive=recursive)

        self.properties = {prop.key: prop for prop in self.schema.properties}
        self.emit('created', self)

    def __getattr__(self, attr):
        if attr in self.properties:
            return self.get(attr, self.properties[attr].default)
        msg = "'{0}' object has no attribute '{1}'"
        raise AttributeError(msg.format(type(self).__name__, attr))

    def __dir__(self):
        return sorted(set(dir(type(self)) + list(self.__dict__) +
                      self.properties.keys()))

    @property
    def schema(self):
        return Context().schema.resource(self.type)

    def check(self):
        """Check that the resource exists.

        :raises ResourceNotFound: if the resource doesn't exists
        """
        if self.fq_name:
            self['uuid'] = self._check_fq_name(self.fq_name)
        elif self.uuid:
            self['fq_name'] = self._check_uuid(self.uuid)
        return True

    @http_error_handler
    def _check_uuid(self, uuid):
        return self.session.id_to_fqname(uuid, type=self.type)['fq_name']

    @http_error_handler
    def _check_fq_name(self, fq_name):
        return self.session.fqname_to_id(fq_name, self.type)

    @property
    def exists(self):
        """Returns True if the resource exists on the API server,
        or returns False.

        :rtype: bool
        """
        try:
            self.check()
        except ResourceNotFound:
            return False
        return True

    @property
    def uuid(self):
        """Return UUID of the resource

        :rtype: str
        """
        return self.get('uuid', super(Resource, self).uuid)

    @property
    def fq_name(self):
        """Return FQDN of the resource

        :rtype: FQName
        """
        return self.get('fq_name', self.get('to', super(Resource, self).fq_name))

    @property
    def parent(self):
        """Return parent resource

        :rtype: Resource
        :raises ResourceNotFound: parent resource doesn't exists
        :raises ResourceMissing: parent resource is not defined
        """
        try:
            return Resource(self['parent_type'], uuid=self['parent_uuid'], check=True)
        except KeyError:
            raise ResourceMissing('%s has no parent resource' % self)

    @parent.setter
    def parent(self, resource):
        """Set parent resource

        :param resource: parent resource
        :type resource: Resource

        :raises ResourceNotFound: resource not found on the API
        """
        resource.check()
        self['parent_type'] = resource.type
        self['parent_uuid'] = resource.uuid

    @property
    def created(self):
        """Return creation date

        :rtype: datetime
        :raises ResourceNotFound: resource not found on the API
        """
        if 'id_perms' not in self:
            self.fetch()
        created = self['id_perms']['created']
        return datetime.strptime(created, '%Y-%m-%dT%H:%M:%S.%f')

    @http_error_handler
    def save(self):
        """Save the resource to the API server

        If the resource doesn't have a uuid the resource will be created.
        If uuid is present the resource is updated.

        :rtype: Resource
        """
        if self.path.is_collection:
            self.session.post_json(self.href,
                                   {self.type: dict(self.data)},
                                   cls=ResourceEncoder)
        else:
            self.session.put_json(self.href,
                                  {self.type: dict(self.data)},
                                  cls=ResourceEncoder)
        return self.fetch(exclude_children=True, exclude_back_refs=True)

    @http_error_handler
    def delete(self):
        """Delete resource from the API server
        """
        res = self.session.delete(self.href)
        self.emit('deleted', self)
        return res

    @http_error_handler
    def fetch(self, recursive=1, exclude_children=False, exclude_back_refs=False):
        """Fetch resource from the API server

        :param recursive: level of recursion for fetching resources
        :type recursive: int
        :param exclude_children: don't get children references
        :type exclude_children: bool
        :param exclude_back_refs: don't get back_refs references
        :type exclude_back_refs: bool

        :rtype: Resource
        """
        if not self.path.is_resource and not self.path.is_uuid:
            self.check()
        params = {}
        # even if the param is False the API will exclude resources
        if exclude_children:
            params['exclude_children'] = True
        if exclude_back_refs:
            params['exclude_back_refs'] = True
        data = self.session.get_json(self.href, **params)[self.type]
        self.from_dict(data)
        return self

    def from_dict(self, data, recursive=1):
        """Populate the resource from a python dict

        :param recursive: level of recursion for fetching resources
        :type recursive: int
        """
        # Find other linked resources
        data = self._encode_resource(data, recursive=recursive)
        self.data = data

    def _encode_resource(self, data, recursive=1):
        for attr in ('fq_name', 'to'):
            if attr in data:
                data[attr] = FQName(data[attr])
        data = self.refs.encode(data, recursive)
        data = self.back_refs.encode(data, recursive)
        data = self.children.encode(data, recursive)
        return data

    @property
    def refs(self):
        """Return refs resources of the resource

        :rtype: LinkedResources
        """
        return LinkedResources(LinkType.REF, self)

    @property
    def back_refs(self):
        """Return back_refs resources of the resource

        :rtype: LinkedResources
        """
        return LinkedResources(LinkType.BACK_REF, self)

    @property
    def children(self):
        """Return children resources of the resource

        :rtype: LinkedResources
        """
        return LinkedResources(LinkType.CHILDREN, self)

    def remove_ref(self, ref):
        """Remove reference from self to ref

        >>> iip = Resource('instance-ip',
                           uuid='30213cf9-4b03-4afc-b8f9-c9971a216978',
                           fetch=True)
        >>> for vmi in iip['virtual_machine_interface_refs']:
                iip.remove_ref(vmi)
        >>> iip['virtual_machine_interface_refs']
        KeyError: u'virtual_machine_interface_refs'

        :param ref: reference to remove
        :type ref: Resource

        :rtype: Resource
        """
        self.session.remove_ref(self, ref)
        return self.fetch()

    def remove_back_ref(self, back_ref):
        """Remove reference from back_ref to self

        :param back_ref: back_ref to remove
        :type back_ref: Resource

        :rtype: Resource
        """
        back_ref.remove_ref(self)
        return self.fetch()

    def add_ref(self, ref, attr=None):
        """Add reference to resource

        :param ref: reference to add
        :type ref: Resource

        :rtype: Resource
        """
        self.session.add_ref(self, ref, attr)
        return self.fetch()

    def add_back_ref(self, back_ref, attr=None):
        """Add reference from back_ref to self

        :param back_ref: back_ref to add
        :type back_ref: Resource

        :rtype: Resource
        """
        back_ref.add_ref(self, attr)
        return self.fetch()

    def json(self):
        """Return JSON representation of the resource
        """
        return to_json(self.data, cls=ResourceEncoder)


class Actions:
    STORE = 'STORE'
    DELETE = 'DELETE'


class ResourceCache(object):
    """Resource cache of discovered resources.
    """
    def __init__(self):
        self.cache = {
            'resources': datrie.Trie(string.printable),
            'collections': datrie.Trie(string.printable)
        }
        Resource.register('created', self._add_item)
        Resource.register('deleted', self._del_item)
        Collection.register('created', self._add_item)
        Collection.register('deleted', self._del_item)

    def search_resources(self, strings, limit=None):
        return self._search(self.cache['resources'], strings, limit=limit)

    def search_collections(self, strings, limit=None):
        return self._search(self.cache['collections'], strings, limit=limit)

    def search(self, strings, limit=None):
        return self.search_collections(strings, limit=limit) + \
            self.search_resources(strings, limit=limit)

    def _search(self, trie, strings, limit=None):
        """Search in cache

        :param strings: list of strings to get from the cache
        :type strings: str list
        :param limit: limit search results
        :type limit: int

        :rtype: [Resource | Collection]
        """
        results = [trie.has_keys_with_prefix(s) for s in strings]
        if not any(results):
            return []
        for result, s in zip(results, strings):
            if result is True:
                return trie.values(s)[:limit]

    def _get_trie_for_item(self, item):
        if isinstance(item, Collection):
            trie = self.cache['collections']
        elif isinstance(item, Resource):
            trie = self.cache['resources']
        else:
            raise RuntimeError('Invalid item')
        return trie

    def _get_keys(self, item):
        if item.fq_name:
            yield '/%s/%s' % (item.type, item.fq_name)
        yield text_type(item.path)

    def _add_item(self, item):
        trie = self._get_trie_for_item(item)
        for key in self._get_keys(item):
            trie[key] = item

    def _del_item(self, item):
        trie = self._get_trie_for_item(item)
        for key in self._get_keys(item):
            try:
                del trie[key]
            except KeyError:
                pass

    def get_completions(self, word_before_cursor, context, option=None):
        cache_type, type, attr = option.complete.split(':')

        if attr == 'path':
            path = context.current_path / word_before_cursor
            if type and path.base != type:
                raise StopIteration
        else:
            path = Path('/')
            if type:
                path = path / type
            path = path / word_before_cursor

        logger.debug('Search for %s' % path)
        results = getattr(self, 'search_' + cache_type)([text_type(path)])
        seen = set()
        for r in results:
            if (r.type, r.uuid) in seen:
                continue
            seen.add((r.type, r.uuid))
            if attr == 'path':
                value = text_type(r.path.relative_to(context.current_path))
            else:
                value = text_type(getattr(r, attr))
            if attr == 'fq_name':
                meta = r.uuid
            else:
                meta = text_type(r.fq_name)
            if value:
                yield Completion(value,
                                 -len(word_before_cursor),
                                 display_meta=meta)
