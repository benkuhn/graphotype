from . import SchemaCreator

class Adapter(SchemaCreator):
    def __init__(self):
        super().__init__(None, None, [])
    def adapt(self, t):
        return self.map_type(t)
