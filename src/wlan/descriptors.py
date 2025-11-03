class static_property(property):
    """A descriptor to create a class-level property."""

    def __get__(self, obj, cls):
        return self.fget(cls)
