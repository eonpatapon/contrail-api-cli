"""This module creates schema data structure by parsing Contrail
schema files.

>>> list_available_schema_version()
>>> schema = create_schema_from_version("2.21")
>>> schema.all_resources()
>>> schema.resource('virtual-network').children

"""

from os import listdir
from os.path import isfile, join
import logging

import contrail_api_cli.idl_parser
from .utils import to_json

logger = logging.getLogger(__name__)

default_schemas_directory_name = "schemas"
default_schemas_directory_path = join(contrail_api_cli.__path__[0],
                                      default_schemas_directory_name)


class SchemaVersionNotAvailable(Exception):
    def __init__(self, version):
        self.version = version
        msg = "Schema version %s is not available" % self.version
        Exception.__init__(self, msg)


class ResourceNotDefined(Exception):
    def __init__(self, resource_name):
        self.resource_name = resource_name
        msg = "Resource '%s' is not defined in the schema" % self.resource_name
        Exception.__init__(self, msg)


def get_last_schema_version():
    """Return the last available schema version. Version are
    lexicographically sorted. If no version is available, return None.

    :rtype: str or None
    """
    versions = list_available_schema_version()
    if len(versions) > 0:
        return sorted(versions)[-1]
    else:
        return None


def list_available_schema_version():
    """To discover available schema versions."""
    return listdir(default_schemas_directory_path)


def _get_schema_version_path(version):
    if version in list_available_schema_version():
        return join(default_schemas_directory_path, version)
    else:
        raise SchemaVersionNotAvailable(version)


def _get_xsd_from_directory(pathname):
    xsd_files = []
    for f in listdir(pathname):
        abspath = join(pathname, f)
        if isfile(abspath) and abspath.endswith(".xsd"):
            xsd_files.append(abspath)
    return xsd_files


def _parse_xsd_file(filename):
    with open(filename) as f:
        ifmap_statements = contrail_api_cli.idl_parser.IDLParser().Parse(f)
        # idl parser should return empty dict
        if ifmap_statements is None:
            ifmap_statements = {}
        return ifmap_statements


def create_schema_from_version(version):
    """Provide a version of the schema to create it. Use
    list_available_schema_version to discover available versions.

    """
    schema_directory = _get_schema_version_path(version)
    return create_schema_from_xsd_directory(schema_directory)


def create_schema_from_xsd_directory(directory):
    """Create and fill the schema from a directory which contains xsd
    files. It calls fill_schema_from_xsd_file for each xsd file
    found.

    """
    schema = Schema()
    for f in _get_xsd_from_directory(directory):
        logger.info("Loading schema %s" % f)
        fill_schema_from_xsd_file(f, schema)
    return schema


def fill_schema_from_xsd_file(filename, schema):
    """From an xsd file, it fills the schema by creating needed
    Resource. The generateds idl_parser is used to parse ifmap
    statements in the xsd file.

    """
    ifmap_statements = _parse_xsd_file(filename)

    for v in ifmap_statements.values():
        if (isinstance(v[0],
                       contrail_api_cli.idl_parser.IDLParser.Link)):
            src_name = v[1]
            target_name = v[2]
            src = schema._get_or_add_resource(src_name)
            target = schema._get_or_add_resource(target_name)
            if "has" in v[3]:
                src.children.append(target_name)
                target.parent = src_name
            if "ref" in v[3]:
                src.refs.append(target_name)
                target.back_refs.append(src_name)


class Schema(object):
    def __init__(self):
        self._schema = {}

    def resource(self, resource_name):
        try:
            return self._schema[resource_name]
        except KeyError:
            raise ResourceNotDefined(resource_name)

    def all_resources(self):
        return self._schema.keys()

    def _get_or_add_resource(self, resource_name):
        if resource_name not in self._schema:
            self._schema[resource_name] = Resource()
        return self._schema[resource_name]


class Resource(object):
    def __init__(self):
        self.children = []
        self.parent = None
        self.refs = []
        self.back_refs = []

    def json(self):
        data = {'children': self.children,
                'parent': self.parent,
                'refs': self.refs,
                'back_refs': self.back_refs}
        return to_json(data)
