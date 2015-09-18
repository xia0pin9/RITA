from app import app

import analysis
import importers

class Registry(object):
    def __init__(self):
        """ Call down to analysis and get all of our modules registered """
        self.m = analysis.Register()
        self.i = importers.Register()

        # Apply unique ids to each of the modules
        for i in xrange(0, len(self.m)):
            self.m[i].id = i

        for i in xrange(0, len(self.i)):
            self.i[i].id = i
            
    # Returns a list of registered modules
    def GetModules(self):
        return self.m

    def GetImporters(self):
        return self.i 
    
    def SetGlobal(self, opt, key):
        for i in range(0, len(self.GetModules())):
            self.GetModules()[i].SetOption(opt, key)
        for i in range(0, len(self.GetImporters())):
            self.GetImporters()[i].SetOption(opt, key)
        return {'success': True}

