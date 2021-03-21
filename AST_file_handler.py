import gzip
import pandas as pd
import gzip
from anytree.exporter import JsonExporter
import sys
from io import BytesIO

class AstFileHandler:
    def __init__(self, output_folder, use_compression, manager):
        self.output_folder = output_folder
        self.use_compression = use_compression
        # self.df = pd.DataFrame(columns=['id', 'AST'])
        self.df = manager.list()
        self.first_save = True
        self.manager = manager
        
        # Create exporter to export the tree to JSON format
        self.exporter = JsonExporter(indent=2)


    def add_ast(self, ast, id):
        output = self.exporter.export(ast)

        self.df.append({'id': id, 'AST' : output})



    def save(self):
        if self.first_save:
            pd.DataFrame(list(self.df)).to_csv(
                f'{self.output_folder}asts.csv{".bz2" if self.use_compression else ""}',
                index=False)
            self.first_save = False
        else:
            pd.DataFrame(list(self.df)).to_csv(
                f'{self.output_folder}asts.csv{".bz2" if self.use_compression else ""}',
                header=False, 
                index=False, 
                mode='a')

        self.df = self.manager.list()