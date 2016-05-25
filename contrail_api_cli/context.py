class SchemaNotInitialized(Exception):
    pass


class Context(object):
    _instance = None

    _schema = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
        return class_._instance

    @property
    def schema(self):
        if self._schema is None:
            raise SchemaNotInitialized("The schema must be fisrt initialized")
        else:
            return self._schema

    @schema.setter
    def schema(self, schema):
        self._schema = schema
