from __future__ import unicode_literals

from six import text_type

from gevent import GreenletExit


class CommandNotFound(Exception):
    pass


class CommandError(Exception):
    pass


class CommandInvalid(Exception):
    pass


class AbsPathRequired(Exception):
    pass


class ResourceMissing(Exception):
    pass


class NotFound(GreenletExit):

    def __init__(self, resource=None, collection=None):
        super(GreenletExit, self).__init__()
        self.r = resource
        self.c = collection

    def __str__(self):
        return "No resource found"


class ResourceNotFound(NotFound):

    def __str__(self):
        if self.r is None:
            return "Resource not found"
        return "Resource %s not found" % self.r.path \
            if self.r.path.is_uuid \
            else "Resource %s/%s not found" % \
            (self.r.type, text_type(self.r.fq_name))


class CollectionNotFound(NotFound):

    def __str__(self):
        if self.c is None:
            return "Collection not found"
        return "Collection %s not found" % self.c.path


class Exists(GreenletExit):

    def __init__(self, resources=None):
        self.resources = []
        if resources is not None:
            self.resources = resources

    @property
    def _paths(self):
        return ", ".join([text_type(c.path) for c in self.resources])

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join([repr(r) for r in self.resources]))


class ChildrenExists(Exists):

    def __str__(self):
        return "Children %s exists" % self._paths


class BackRefsExists(Exists):

    def __str__(self):
        return "Back references from %s exists" % self._paths
