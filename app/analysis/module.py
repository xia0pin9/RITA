import abc

class Module(object):
    def __init__(self, name, description, options):
        self.name = name
        self.description = description
        self.options = options
    
    @abc.abstractmethod
    def RunModule():
        """Implemented by the Module"""
