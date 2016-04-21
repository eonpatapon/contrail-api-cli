from __future__ import unicode_literals

from six import text_type


class CommandNotFound(Exception):
    pass


class CommandError(Exception):
    pass


class BadPath(Exception):
    pass


class ResourceMissing(Exception):
    pass


class ResourceNotFound(Exception):

    def __init__(self, resource=None):
        super(Exception, self).__init__()
        self.r = resource

    def __str__(self):
        if self.r is None:
            return "Resource not found"
        return "Resource %s not found" % self.r.path \
            if self.r.path.is_resource else text_type(self.r.fq_name)


class NoResourceFound(Exception):

    def __str__(self):
        return "No resource found"
