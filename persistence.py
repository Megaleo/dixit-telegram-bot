import json
import ast
from telegram.ext import DictPersistence
from telegram import User
from game import Stage, EndCriterion, Card, Player, DixitResults, DixitGame 

# List of attributes of classes to save
classes_attrs = \
     {'User'        : ['id', 'is_bot', 'first_name', 'last_name', 'username', 'language_code', 'can_join_groups', 'can_read_all_group_messages', 'supports_inline_queries'], # No bot
     'Card'         : ['image_id', 'id'],
     'Player'       : ['user', 'hand', 'name', 'id'],
     'DixitResults' : ['game_id', 'game_number', 'round_number', 'players', 'storyteller', 'votes', 'table', 'clue', 'score', 'delta_score'],
     'DixitGame'    : ['_stage', 'players', 'master', '_storyteller', 'clue', 'cards', 'table', 'votes', 'end_criterion', 'end_criterion_number', '_draw_pile', 'cards_per_player', 'discard_pile', 'score', 'delta_score', 'lobby', 'round_number', 'game_number', 'game_id']
     }

def encode_dixit(x):
    type_name = x.__class__.__name__
    if type_name in classes_attrs.keys():
        if type_name == 'User':
            class_dict = ast.literal_eval(str(x))
        else:
            class_dict = x.__dict__
        attrs = classes_attrs[type_name]
        json_dict = {k : class_dict[k] 
                     for k in attrs if k in class_dict.keys()}
        json_dict["class_name"] = type_name
        return json_dict
    elif type_name in ['Stage', 'EndCriterion']:
        json_dict = {"name": x.name}
        json_dict["class_name"] = type_name
    elif type_name == 'UUID':
        json_dict = {"int": x.int}
        json_dict["class_name"] = type_name
    else:
        raise TypeError(f"Object of type '{type_name}' is not JSON serializable")

class DixitPersistence(DictPersistence):
    '''Persistence class the inherits from DictPersistence'''

    def __init__(self, base_filename = "data/dixit"):
        super().__init__(store_bot_data=False)
        self.base_filename = base_filename

    @property
    def chat_data_json(self):
        if self._chat_data_json:
            return self._chat_data_json
        return json.dumps(self.chat_data, default=encode_dixit)

    def update_chat_data(self, chat_id, data):
        super().update_chat_data(chat_id, data)
        with open(f"{self.base_filename}_chat_data.json", "w") as file:
            file.write(self.chat_data_json)

    def update_user_data(self, user_id, data):
        super().update_user_data(user_id, data)
        with open(f"{self.base_filename}_user_data.json", "w") as file:
            file.write(self.user_data_json)
    
    def flush(self):
        with open(f"{self.base_filename}_chat_data.json", "w") as file:
            file.write(self.chat_data_json)
        with open(f"{self.base_filename}_user_data.json", "w") as file:
            file.write(self.user_data_json)

