from app import app

import analysis

class Registry(object):
    def __init__(self):
        self.r = analysis.Register()

    def GetModules(self):
        print(self.r)
        return self.r
