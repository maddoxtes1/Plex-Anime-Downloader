import json
import os


class compare_json:
    def __init__(self, episode_json, Anime_json):
        self.episode_json = episode_json
        self.Anime_json = Anime_json

        self.new_episode = self.execute()

    def execute(self):
        with open(self.episode_json, 'r', encoding='utf-8') as file1:
            data1 = json.load(file1)
        
        if not os.path.exists(self.Anime_json):
            json_structure = {}
            with open(self.Anime_json, 'w') as json_file:
                json.dump(json_structure, json_file, indent=4)

        with open(self.Anime_json, 'r', encoding='utf-8') as file2:
            data2 = json.load(file2)
            
        new_entries = []
        
        keys2 = {int(k) for k in data2.keys() if k.isdigit()}
        
        for key in data1:
            num_key = int(key)
            if num_key not in keys2:
                new_entries.append((key, data1[key]))
        return new_entries