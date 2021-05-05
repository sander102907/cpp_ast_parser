import os
import json
import hashlib

class Tokenizer:
    def __init__(self, out_path, tokenized=False):
        self.out_path = out_path
        self.token_dict = {}
        self.label_dict = {}

        # Tokenizer can also be used as counter 
        # Instead of tokenizing, count how many times each label occurs
        # tokenizer should then be set to False
        self.tokenized = tokenized


    # Returns the token from a label, creates tokens for new labels
    def get_token(self, label):
        if label in self.token_dict:
            if self.tokenized:
                return self.token_dict[label]
            else:
                self.token_dict[label] += 1
                return label
        else:
            if self.tokenized:
                token = len(self.token_dict)
                self.token_dict[label] = token
                self.label_dict[token] = label
                return token
            else:
                self.token_dict[label] = 1
                return label

                
    # Return the label from a token
    def get_label(self, token):
        if self.tokenized:
            if token in self.label_dict:
                return self.label_dict[token]
            else:
                return token
        else:
            return token


    # Saves tokenizer to file
    def save(self):
        if not self.out_path:
            return

        json_f = json.dumps(self.token_dict)
        f = open(self.out_path, 'w')
        f.write(json_f)
        f.close()

    
    # Loads tokenizer from file
    def load(self, path):
        with open(path, 'r') as json_f:
            json_data = json_f.read()

        self.token_dict = json.loads(json_data)

        # Reverse the token dict to create a label dict
        self.label_dict = dict((reversed(item) for item in self.token_dict.items()))


    # Clears the tokenizer
    def clear(self):
        self.token_dict.clear()
        self.label_dict.clear()


    # Merges this tokenizer with another tokenizer
    def merge(self, tokenizer):
        if self.tokenized:
            for label in tokenizer.token_dict.keys():
                if label not in self.token_dict:
                    token = len(self.token_dict)
                    self.token_dict[label] = token
                    self.label_dict[token] = label
        else:
            for k,v in tokenizer.token_dict.items():
                if k in self.token_dict:
                    self.token_dict[k] += v
                else:
                    self.token_dict[k] = v
