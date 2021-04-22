import gzip
import pandas as pd
import gzip
from anytree.exporter import JsonExporter
import sys
from io import BytesIO

class AstFileHandler:
    def __init__(self, output_folder, use_compression, process_nr=0):
        self.output_folder = output_folder
        self.use_compression = use_compression
        self.df = pd.DataFrame(columns=['id', 'AST'])
        self.first_save = True
        self.process_nr = process_nr
        
        # Create exporter to export the tree to JSON format
        self.exporter = JsonExporter(indent=2)


    def add_ast(self, ast, id):
        output = self.exporter.export(ast)

        self.df = self.df.append([{'id': id, 'AST' : output}], ignore_index=True)



    def save(self):
        if self.first_save:
            self.df.to_csv(
                f'{self.output_folder}asts{self.process_nr}.csv{".bz2" if self.use_compression else ""}',
                index=False)
            self.first_save = False
        else:
            self.df.to_csv(
                f'{self.output_folder}asts{self.process_nr}.csv{".bz2" if self.use_compression else ""}',
                header=False, 
                index=False, 
                mode='a')

        self.df = pd.DataFrame(columns=['id', 'AST'])