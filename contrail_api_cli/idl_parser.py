"""
idl_parser.py

Parse IDL statements embedded in a XML schema file.

Copyright (c) 2013 Contrail Systems. All rights reserved.
"""

import logging
import os
import re
import sys


class IDLParser(object):
    class Property(object):
        def __init__(self, prop_name,
                     presence='optional',
                     operations='CRUD',
                     description='',
                     **kwargs):
            self.name = prop_name
            self.is_list = kwargs.get('is_list', 'False')
            self.is_map = kwargs.get('is_map', 'False')
            self.map_key_name = kwargs.get('map_key_name')
            self.presence = presence
            self.operations = operations
            self.description = description

        def IsList(self):
            return self.is_list is True

        def IsMap(self):
            return self.is_map is True
    # end class Property

    class Link(object):
        def __init__(self, link_name,
                     presence='optional',
                     operations='CRUD',
                     description='',
                     **kwargs):
            self.name = link_name
            self.presence = presence
            self.operations = operations
            self.description = description
    # end class Link

    def __init__(self):
        self._ElementDict = {}

    def Parse(self, infile):
        xml_comment = re.compile(r'<!--\s*#IFMAP-SEMANTICS-IDL(.*?)-->',
                                 re.DOTALL)
        file_matches = xml_comment.findall(infile.read())
        # Remove newline, split at stmt boundary
        matches = [re.sub('\n', '', match).split(';') for match in file_matches]
        for statements in matches:
            for stmt in statements:
                # Oper in idl becomes method
                try:
                    eval("self._%s" % (stmt.lstrip()))
                except TypeError:
                    logger = logging.getLogger('idl_parser')
                    logger.debug('ERROR statement: %s', stmt)
                # self._ParseExpression(stmt)
        return self._ElementDict

    def Find(self, element):
        return self._ElementDict.get(element)

    def IsProperty(self, annotation):
        return isinstance(annotation[0], IDLParser.Property)

    def IsAllProperty(self, annotation):
        return (isinstance(annotation[0], IDLParser.Property) and
                'all' in annotation[1])

    def IsLink(self, annotation):
        return isinstance(annotation[0], IDLParser.Link)

    def GetLinkInfo(self, link_name):
        if link_name in self._ElementDict:
            idl_link, from_name, to_name, attrs = self._ElementDict[link_name]
            return (from_name, to_name, attrs)
        else:
            return (None, None, None)

    def _Type(self, type_name, attrs):
        logger = logging.getLogger('idl_parser')
        logger.debug('Type(%s, %s)', type_name, attrs)

    def _Property(self, prop_name, ident_name,
                  *args, **kwargs):
        logger = logging.getLogger('idl_parser')
        logger.debug('Property(%s, %s)', prop_name, ident_name)
        try:
            idl_prop, idents = self._ElementDict[prop_name]
            idents.append(ident_name)
        except KeyError:
            idl_prop = IDLParser.Property(prop_name, *args, **kwargs)
            self._ElementDict[prop_name] = (idl_prop, [ident_name])

    def _ListProperty(self, prop_name, ident_name,
                      *args, **kwargs):
        logger = logging.getLogger('idl_parser')
        logger.debug('ListProperty(%s, %s)', prop_name, ident_name)
        try:
            idl_prop, idents = self._ElementDict[prop_name]
            idents.append(ident_name)
        except KeyError:
            idl_prop = IDLParser.Property(
                prop_name, *args, is_list=True, **kwargs)
            self._ElementDict[prop_name] = (idl_prop, [ident_name])

    def _MapProperty(self, prop_name, ident_name, key_name,
                     *args, **kwargs):
        logger = logging.getLogger('idl_parser')
        logger.debug('MapProperty(%s, %s)', prop_name, ident_name)
        try:
            idl_prop, idents = self._ElementDict[prop_name]
            idents.append(ident_name)
        except KeyError:
            idl_prop = IDLParser.Property(
                prop_name, *args, is_map=True, map_key_name=key_name, **kwargs)
            self._ElementDict[prop_name] = (idl_prop, [ident_name])

    def _Exclude(self, elem_name, excluded):
        logger = logging.getLogger('idl_parser')
        logger.debug('Exclude(%s, %s)', elem_name, excluded)

    def _Link(self, link_name, from_name, to_name, attrs,
              *args, **kwargs):
        logger = logging.getLogger('idl_parser')

        mch = re.match(r'(.*):(.*)', from_name)
        if mch:
            # from_ns = mch.group(1)
            from_name = mch.group(2)

        mch = re.match(r'(.*):(.*)', to_name)
        if mch:
            # to_ns = mch.group(1)
            to_name = mch.group(2)

        # TODO store and handle namespace in identifiers

        logger.debug('Link(%s, %s, %s)', from_name, to_name, attrs)
        idl_link = IDLParser.Link(link_name, *args, **kwargs)
        self._ElementDict[link_name] = (idl_link, from_name, to_name, attrs)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Usage: %s schema.xsd' % sys.argv[0])
    if not os.path.exists(sys.argv[1]):
        sys.exit('Error: %s not found' % sys.argv[1])
    idl_parser = IDLParser()
    idl_parser.Parse(sys.argv[1])
