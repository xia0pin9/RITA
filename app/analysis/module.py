import abc

class Module(object):
    def __init__(self, name, description, options):
        self.name = name
        self.global_options = ["customer"]
        self.description = description
        self.options = options
    
    def SetOption(self, key, value):
        if key in self.options:
            self.options[key] = value
            return True
        return False
    
    def GetOptions(self):
        ret = {}
        for opt in self.options:
            if opt not in self.global_options:
                ret[opt] = self.options[opt]
        return ret

    @abc.abstractmethod
    def RunModule():
        """Implemented by the Module"""
