import json

class JsonFileReader:
    DATA_FILENAME = None

    def __init__(self, filename):
        self.DATA_FILENAME = filename

        
    def read_file(self):
        try:
            with open(self.DATA_FILENAME, "r") as f:
                data = json.load(f)
        except TypeError:
            data = {}
        return data
