import ConfigParser
class MyraConfig(object):
    def __init__(self, config_file = None):
        self.config_file = config_file
        if not self.config_file:
            self.config_file = "./settings.conf"
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.config_file)

    def get(self, section):
        res = {}
        options = self.config.options(section)
        for option in options:
            try:
                res[option] = self.config.get(section, option)
                if res[option] == -1:
                    pass # Skip
            except:
                print("exception on %s!" % option)
                res[option] = None
        return res




