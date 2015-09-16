from app import app

import analysis

class Registry(object):
    def __init__(self):
        """ Call down to analysis and get all of our modules registered """
        self.r = analysis.Register()
        
        # Apply unique ids to each of the modules
        for i in xrange(0, len(self.r)):
            self.r[i].id = i

    # Returns a list of registered modules
    def GetModules(self):
        print(self.r)
        return self.r
