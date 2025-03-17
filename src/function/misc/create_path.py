import os

class create_path:
    def __init__(self, path):
        if not os.path.exists(path):
            os.makedirs(path)