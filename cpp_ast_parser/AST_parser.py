import os
import clang.cindex
from clang.cindex import CursorKind
from tree_node import Node
import utils
from node_handler import NodeHandler
from tqdm import tqdm
import threading
import multiprocessing
import queue as queue
import json
import pandas as pd
import subprocess
from tokenizer import Tokenizer
import gzip
from AST_file_handler import AstFileHandler
from datetime import datetime
import math
import ccsyspath



"""
The AST Parser that can take as input a CSV file containing data of C++ programs:
- Name/ID (solutionId)
- Code (solution)
- Imports -> includes and usings (imports)

Output for each program in the CSV file an AST in JSON format, where each node contains a label
of what this node represents in the code (e.g. function declaration) and whether this label is a reserved
item from the language (so not a variable name for example)
"""

class AstParser:
    def __init__(self, clang_lib_file, csv_file_path, output_folder, use_compression, processes_num, split_terminals, tokenized, mpi):
        # Try to set a library file for clang
        try:
            clang.cindex.Config.set_library_file(clang_lib_file)
        except Exception as e:
            print('Skipped setting library file: {}'.format(e))

        # Create index object to parse with
        self.index = clang.cindex.Index.create()

        # CSV to get program data from
        self.csv_file_path = csv_file_path

        # Output folder to save data to
        self.output_folder = output_folder

        # # Create reserved label tokenizer
        # self.res_tn = Tokenizer(output_folder + 'reserved_tokens.json', tokenized)

        # # Create non reserved label tokenizer
        # self.tn = Tokenizer(output_folder + 'tokens.json', tokenized)


        # Create AST file handler object
        self.ast_file_handler = AstFileHandler(self.output_folder + 'asts/', use_compression)

        # Boolean whether or not to use compression to save AST files as .gz
        self.use_compression = use_compression

        # Number of parallel processes
        self.processes_num = processes_num

        # Boolean to indicate whether we are using MPI
        self.mpi = mpi

        if mpi:
            from mpi4py import MPI
            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()

            self.tokenizers = {
                'RES': Tokenizer(output_folder + f'reserved_tokens/reserved_tokens_{self.rank}.json', tokenized),
                'NAME': Tokenizer(output_folder + f'name_tokens/name_tokens_{self.rank}.json', tokenized),
                'TYPE': Tokenizer(output_folder + f'type_tokens/type_tokens_{self.rank}.json', tokenized),
                'LITERAL': Tokenizer(output_folder + f'literal_tokens/literal_tokens_{self.rank}.json', tokenized)
            }

            self.ast_file_handler = AstFileHandler(self.output_folder + 'asts/', use_compression, self.rank)
        else:
            self.tokenizers = {
                'RES': Tokenizer(output_folder + 'reserved_tokens/reserved_tokens.json', tokenized),
                'NAME': Tokenizer(output_folder + 'name_tokens.json', tokenized),
                'TYPE': Tokenizer(output_folder + 'type_tokens.json', tokenized),
                'LITERAL': Tokenizer(output_folder + 'literal_tokens.json', tokenized)
            }

            self.ast_file_handler = AstFileHandler(self.output_folder, use_compression)


        # Create node handler object
        self.nh = NodeHandler(self.tokenizers, split_terminals)

    def parse_ast(self, program, imports, thread_nr):
        # Create temp file path for each trhead for clang to save in memory contents
        temp_file_path = f'{self.output_folder}tmp{thread_nr}.cpp'

        # Preprocess the program, expand the macros
        preprocessed_program = self.preprocess_program(program, temp_file_path, imports)

        # Set arguments and add compiler system include paths (with ccsyspath)
        args    = '-x c++ --std=c++20'.split()
        syspath = ccsyspath.system_include_paths('clang')
        incargs = [ b'-I' + inc for inc in syspath ]
        args    = args + incargs

        # Parse the program to a clang AST
        tu = self.index.parse(
                            temp_file_path,
                            unsaved_files=[(temp_file_path, preprocessed_program)],
                            args=args,
                            options=0)

        # Retrieve only the cursor items (children) that contain the program code (no import code)
        cursor_items = self.get_cursor_items(tu.cursor, temp_file_path)

        # Create a root node
        root_node = Node(self.tokenizers['RES'].get_token('root'), is_reserved=True)

        # for cursor_item in cursor_items:
        #     for c in cursor_item.walk_preorder():
        #         print(f'spelling: {c.spelling}, kind: {c.kind.name}, type spelling: {c.type.spelling}, return type: {c.type.get_result().spelling}, type kind: {c.type.kind}')

        # Parse each cursor item
        for cursor_item in cursor_items:
            self.parse_item(cursor_item, root_node, program)


        # Return the root node filled with children to form the AST
        return root_node


    # Retrieves cursor items which are actually located in the program
    # This exludes any directives such as #includes which are preprocessed as well
    def get_cursor_items(self, cursor, input_file_path):
        cursor_items = []

        for child in list(cursor.get_children()):
            if str(child.location.file) == input_file_path:
                cursor_items.append(child)

        return cursor_items

    def preprocess_program(self, program, temp_file_path, imports):
        # Create a temporary file to store program in
        temp_file = open(temp_file_path, 'w')
        temp_file.write(program)
        temp_file.close()

        # Call preprocess g++ function to expand the macros (need this to get operator tokens)
        preprocessed_program = subprocess.check_output(['g++', '-x', 'c++', '-E', temp_file_path]).decode()

        # Only retrieve the actual original code from the program not all the includes
        program_lines = preprocessed_program.split('\n')

        # First get the saved imports (includes)
        imports = [ele for ele in imports[1:-1].split("'") if ele != '' and ele != ', ']

        # Add imports to the first lines of the new filtered program
        preprocessed_program_filtered = '\n'.join([imp for imp in imports if imp.startswith('#')])

        # Select only the lines of the original program
        skip = False
        for l in program_lines:
            if not skip:
                preprocessed_program_filtered += f'{l}\n'
            if l.startswith("# "):
                toks = l.strip().split(" ")
                linenum, filename = toks[1:3]
                flags = toks[3:]
                skip = "3" in flags

        return preprocessed_program_filtered


    # Parse the AST node by node, recursive function starting from the root creating all children
    def parse_item(self, ast_item, parent_node, program):   
        # Useless AST primitives
        skip_kinds = [
            CursorKind.UNEXPOSED_EXPR, CursorKind.OVERLOADED_DECL_REF,
            CursorKind.TEMPLATE_REF
            ]

        # print(ast_item.spelling, ast_item.kind.name, ast_item.type.spelling, [t.spelling for t in ast_item.get_tokens()])


        # Skip useless AST primitives and exceptions -> continue straight with their children
        if ast_item.kind in skip_kinds \
        or 'operatorbool' == ast_item.spelling \
        or 'operator bool' == ast_item.spelling \
        or (('std::string' == ast_item.type.spelling \
        or 'basic_string' == ast_item.spelling) \
        and ast_item.kind in [CursorKind.TYPE_REF, CursorKind.CALL_EXPR]):
            pass

        # Parse typdef
        elif utils.is_typedef(ast_item):
            self.nh.handle_typedef(ast_item, parent_node)

        # parse declaration
        elif ast_item.kind.is_declaration():
            parent_node = self.nh.handle_declaration(ast_item, parent_node, self.parse_item, program)

        # parse operator
        elif utils.is_operator(ast_item):
            parent_node = self.nh.handle_operator(ast_item, parent_node)

        # parse literal
        elif utils.is_literal(ast_item):
            self.nh.handle_literal(ast_item, parent_node, program)


        # parse call expression
        elif utils.is_call_expr(ast_item):
            parent_node = self.nh.handle_call_expr(ast_item, parent_node, self.parse_item, program)


        # parse reference
        elif utils.is_reference(ast_item):
            p_node = self.nh.handle_reference(ast_item, parent_node)

            if p_node:
                parent_node = p_node                    

        # parse type ref
        elif ast_item.kind == CursorKind.TYPE_REF \
            and parent_node\
            and self.tokenizers['RES'].get_label(parent_node.token) not in ['root', 'DECLARATOR',
            'FUNCTION_DECL', 'FUNCTION_TEMPLATE', 'ARGUMENTS',
            'CXX_FUNCTIONAL_CAST_EXPR']:
            self.nh.handle_type_ref(ast_item, parent_node)

        # Parse for range -> for(int a:v) {...}
        elif ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            parent_node = self.nh.handle_for_range(ast_item, parent_node)

        # Parse cast expressions -> (int) a
        elif ast_item.kind == CursorKind.CSTYLE_CAST_EXPR:
            parent_node = self.nh.handle_cast_expr(ast_item, parent_node)

        elif ast_item.kind == CursorKind.CXX_FUNCTIONAL_CAST_EXPR:
            parent_node = self.nh.handle_func_cast_expr(ast_item, parent_node)

        elif ast_item.kind == CursorKind.LAMBDA_EXPR:
            parent_node = self.nh.handle_lambda_expr(ast_item, parent_node, self.parse_item, program)

        elif ast_item.kind == CursorKind.CXX_STATIC_CAST_EXPR:
            parent_node = self.nh.handle_static_cast_expr(ast_item, parent_node)

        elif ast_item.kind == CursorKind.LABEL_REF:
            self.nh.handle_reference(ast_item, parent_node)

        elif ast_item.kind == CursorKind.LABEL_STMT:
            parent_node = self.nh.handle_label_stmt(ast_item, parent_node)

        # if not one of the above -> create simple parent node of the kind of the item
        elif ast_item.kind != CursorKind.TYPE_REF:
            # print(ast_item.spelling, ast_item.kind.name)
            parent_node = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        # Do not iterate through children that we have already treated as arguments
        arguments = []
        if utils.is_call_expr(ast_item):
            arguments = [c.spelling for c in ast_item.get_arguments()]


        # Already handled first child of for range statement, so start from second child
        if ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            for index, child in enumerate(list(ast_item.get_children())[1:]):
                # Add compound statment -> {...} if this is missing
                if index == len(list(ast_item.get_children())[1:]) - 1 and child.kind != CursorKind.COMPOUND_STMT:
                    compound_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt, program)
                else:
                    self.parse_item(child, parent_node, program)

        # Handle one liner if/while statements with no compound statement (={..}) as children -> if (...) return x; ADD COMPOUND STATEMENT ANYWAY
        elif (ast_item.kind == CursorKind.IF_STMT or ast_item.kind == CursorKind.WHILE_STMT)\
             and any(CursorKind.COMPOUND_STMT != child.kind for child in list(ast_item.get_children())[1:]):
            for index, child in enumerate(ast_item.get_children()):
                # print(child.spelling, child.kind.name, child.type.spelling, index)
                if (index != 1 and index < len(list(ast_item.get_children())) - 1) or child.kind == CursorKind.COMPOUND_STMT or child.kind == CursorKind.IF_STMT:
                    self.parse_item(child, parent_node, program)
                else:
                    compound_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt, program)

        # Handle for statements with no compound statement. ADD COMPOUND STATEMENT
        elif (ast_item.kind == CursorKind.FOR_STMT or ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT) and list(ast_item.get_children())[-1].kind != CursorKind.COMPOUND_STMT:
            compound_stmt = None
            for index, child in enumerate(ast_item.get_children()):
                if index < len(list(ast_item.get_children())) - 1 or child.kind == CursorKind.COMPOUND_STMT:
                    self.parse_item(child, parent_node, program)
                else:
                    if compound_stmt is None:
                        compound_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt, program)

        # For while statement, only take first child and compound statements as children
        elif ast_item.kind == CursorKind.WHILE_STMT:
            for index, child in enumerate(ast_item.get_children()):
                if index == 0 or (index > 0 and child.kind == CursorKind.COMPOUND_STMT):
                    self.parse_item(child, parent_node, program)       


        # Standard case, process all the children of the node recursively
        else:
            for child in ast_item.get_children():
                # Param declarations, arguments alreadly handled. 
                # Also skip structure declarations if parent is declarator
                # And skip compound statements if the parent is a constructor
                # And skip array sizes if type of var decl is array, only consider the init list expressions
                if not(child.kind == CursorKind.PARM_DECL or child.spelling in arguments \
                    or (ast_item.kind == CursorKind.STRUCT_DECL 
                    and self.tokenizers['RES'].get_label(parent_node.token) == 'DECLARATOR') \
                    or (parent_node and parent_node.token
                    and self.tokenizers['RES'].get_label(parent_node.token) == 'CONSTRUCTOR'
                    and child.kind != CursorKind.COMPOUND_STMT)\
                    or (ast_item.kind in [CursorKind.VAR_DECL, CursorKind.FIELD_DECL]
                    and 'TYPE_ARRAY' in [self.tokenizers['RES'].get_label(c.token) for c in parent_node.parent.children[0].children] +
                     [self.tokenizers['RES'].get_label(c.token) for c in parent_node.parent.children[1].children]
                    and child.kind != CursorKind.INIT_LIST_EXPR)):

                    self.parse_item(child, parent_node, program)


    def thread_parser(self, file_queue, pbar, thread_nr):
        while not file_queue.empty():
            # Get a program from the queue
            program_id, code, imports = file_queue.get()
            try:
                # Parse the AST tree for the program
                ast = self.parse_ast(code, imports, thread_nr)
            except Exception as e:
                print(f'Skipping file due to parsing failing: {program_id} - {e}')
                pbar.set_description(f'{datetime.now()}')
                pbar.update()
                file_queue.task_done()
                continue

            # Write the AST tree to file
            self.ast_file_handler.add_ast(ast, program_id)


            # Mark as done    
            pbar.set_description(f'{datetime.now()}')
            pbar.update()
            file_queue.task_done()


    def mpi_parser(self, files, process_nr):
        for file in tqdm(files, postfix=f'process: {process_nr}'):
            program_id, code, imports = file
            try:
                # Parse the AST tree for the program
                ast = self.parse_ast(code, imports, process_nr)
            except Exception as e:
                print(f'Skipping file due to parsing failing: {program_id} - {e}')
                # pbar.set_description(f'{datetime.now()}')
                # pbar.update()
                # file_queue.task_done()
                continue

            # Write the AST tree to file
            self.ast_file_handler.add_ast(ast, program_id)


    def clear_temp_files(self):
        if self.mpi:
            os.remove(f'{self.output_folder}tmp{self.rank}.cpp')
        else:
            for i in range(self.processes_num):
                os.remove(f'{self.output_folder}tmp{i}.cpp')


    def __cleanup(self):
        # Save tokens to file
        for tokenizer in self.tokenizers.values():
            tokenizer.save()

        self.ast_file_handler.save()
        

        # Clear the temporary files
        try:
            self.clear_temp_files()
        # If number of files < number of threads, there less temp files than we want to remove
        except FileNotFoundError:
            pass


    def parse_csv(self):
        print('Parsing programs ...')

        # Create output directory if it does not exist yet
        os.makedirs(self.output_folder, exist_ok=True)

        # Read csv file in chunks (may be very large)
        programs = pd.read_csv(self.csv_file_path, chunksize=1e5)

        # iterate over the chunks
        for i, programs_chunk in enumerate(programs):
            # Create progressbar
            pbar = tqdm(total=len(programs_chunk), unit=' program', postfix=f'chunk {i}', colour='green', disable=False)
            # Create file queue to store the program data
            file_queue = queue.Queue(len(programs_chunk))

            # Fill the queue with files.
            for program in list(programs_chunk[['solutionId', 'solution', 'imports']].iterrows()):
                # if program[1]['solutionId'] == 44591144:
                    file_queue.put((program[1]['solutionId'], program[1]['solution'], program[1]['imports']))
                    # break
            

            try:
                threads = []
                # Create threads which parse ASTs
                for thread_nr in range(self.processes_num):
                    t = threading.Thread(target=self.thread_parser,
                                        args=(file_queue, pbar, thread_nr))
                    t.daemon = True
                    t.start()
                    threads.append(t)

                # Wait for all threads to be done.
                file_queue.join()    
                for thread in threads:
                    thread.join()              
                self.ast_file_handler.save()
                                

            # Exit program with keyboard interrupt
            except KeyboardInterrupt:
                self.__cleanup()
                os.kill(0, 9)


        self.__cleanup()


    def parse_mpi(self):
        print('Parsing programs ...')

        # Create output directory if it does not exist yet
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.output_folder + 'asts/', exist_ok=True)
        os.makedirs(self.output_folder + 'reserved_tokens/', exist_ok=True)
        os.makedirs(self.output_folder + 'name_tokens/', exist_ok=True)
        os.makedirs(self.output_folder + 'type_tokens/', exist_ok=True)
        os.makedirs(self.output_folder + 'literal_tokens/', exist_ok=True)

        # Read csv file in chunks (may be very large)
        programs = pd.read_csv(self.csv_file_path, chunksize=1e5)

        def get_files():
            files = []

            # Fill the queue with files.
            for program in list(programs_chunk[['solutionId', 'solution', 'imports']].iterrows()):
                # if program[1]['solutionId'] == 104465269:
                    files.append((program[1]['solutionId'], program[1]['solution'], program[1]['imports']))

            return files

        # iterate over the chunks
        for programs_chunk in programs:
            if self.rank == 0:
                files = get_files()
                batch_size = len(files)/self.size
                for i in range(1, self.size):
                    data = files[math.ceil(batch_size * i): math.ceil(batch_size * (i + 1))]
                    self.comm.send(data, dest=i)
                files = files[:math.ceil(batch_size)]
            else:
                files = self.comm.recv(source=0)

            self.mpi_parser(files, self.rank)
            self.__cleanup()
        

        






    



