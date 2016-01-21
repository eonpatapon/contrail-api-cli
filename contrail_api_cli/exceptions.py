from __future__ import unicode_literals


class CommandNotFound(Exception):
    pass


class CommandError(Exception):
    pass


class BadPath(Exception):
    pass


class ResourceMissing(Exception):
    pass


class ResourceNotFound(Exception):

    def __init__(self, uuid=None, fq_name=None):
        super(Exception, self).__init__()
        self.uuid = uuid
        self.fq_name = fq_name

    def __str__(self):
        return "Resource %s not found" % self.uuid or self.fq_name


class NoResourceFound(Exception):

    def __str__(self):
        return "No resource found"
