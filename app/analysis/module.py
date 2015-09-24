import abc

class Module(object):
    def __init__(self, name, description, options):
        self.name = name
        self.global_options = ["customer", "server"]
        self.description = description
        self.options = options
    
    # TODO: Type validation
    def SetOption(self, key, value):
        if key in self.options:
            if self.options[key]["type"] == "number":
                self.options[key]["value"] = float(value)
            elif self.options[key]["type"] == "string":
                self.options[key]["value"] = value
            elif self.options[key]["value"] == "bool":
                if value == "True" or value == "true" or value == True:
                    self.options[key]["value"] = True;
                else:
                    self.options[key]["value"] = False
            else:
                return False
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
