import abc

class Module(object):
    def __init__(self, name, description, options):
        self.name = name
        self.description = description
        self.options = options
    
    def SetOption(self, key, value):
        if key in self.options:
            self.options[key] = value
            return True
        return False

    @abc.abstractmethod
    def RunModule():
        """Implemented by the Module"""
