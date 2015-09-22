import abc

class Module(object):
    def __init__(self, name, description, options):
        self.name = name
        self.global_options = ["customer"]
        self.description = description
        self.options = options
    
    # TODO: Type validation
    def SetOption(self, key, value):
        if key in self.options:
            self.options[key]["value"] = value
            return True
        return False
    
    def GetOptions(self):
        ret = [] 
        for opt in self.options:
            if opt not in self.global_options:
                temp = {
                        "name": opt,
                        "type": self.options[opt]["type"],
                        "value": self.options[opt]["value"]
                        }
                ret.append(temp)

        return ret

    @abc.abstractmethod
    def RunModule(self):
        """Implemented by the Module"""
