from app import app

import analysis

class Registry(object):
    def __init__(self):
        self.r = analysis.Register()

        for i in xrange(0, len(self.r)):
            self.r[i].id = i

    def GetModules(self):
        print(self.r)
        return self.r
