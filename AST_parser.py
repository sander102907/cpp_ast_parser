import os
import clang.cindex
from clang.cindex import CursorKind
from tree_node import Node
import utils
from node_handler import NodeHandler
from tqdm import tqdm
from anytree.exporter import JsonExporter
import threading
import multiprocessing
import queue as queue
import json
import pandas as pd
import subprocess
from tokenizer import Tokenizer

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
    def __init__(self, clang_lib_file, csv_file_path, output_folder):
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

        # Create exporter to export the tree to JSON format
        self.exporter = JsonExporter(indent=2)

        # Create reserved label tokenizer
        self.res_tn = Tokenizer(output_folder + 'reserved_tokens.json')

        # Create non reserved label tokenizer
        self.tn = Tokenizer(output_folder + 'tokens.json')

        # Create node handler object
        self.nh = NodeHandler(self.res_tn, self.tn)


    def parse_ast(self, program, imports, thread_nr):
        # Create temp file path for each trhead for clang to save in memory contents
        temp_file_path = f'tmp{thread_nr}.cpp'

        # Preprocess the program, expand the macros
        preprocessed_program = self.preprocess_program(program, temp_file_path, imports)

        # Parse the program to a clang AST
        tu = self.index.parse(
                            temp_file_path,
                            unsaved_files=[(temp_file_path, preprocessed_program)],
                            args=['-x', 'c++', '-std=c++17'],
                            options=0)

        # Retrieve only the cursor items (children) that contain the program code (no import code)
        cursor_items = self.get_cursor_items(tu.cursor, temp_file_path)

        # Create a root node
        root_node = Node(self.res_tn.get_token('root'), is_reserved=True)

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
        imports = imports[1:-1].replace("'", "").split(', ')

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
            and parent_node and self.res_tn.get_label(parent_node.token) != 'root' \
            and self.res_tn.get_label(parent_node.token) != 'DECLARATOR' \
            and self.res_tn.get_label(parent_node.token) != 'FUNCTION_DECL'\
            and self.res_tn.get_label(parent_node.token) != 'FUNCTION_TEMPLATE'\
            and self.res_tn.get_label(parent_node.token != 'ARGUMENTS'):
            self.nh.handle_type_ref(ast_item, parent_node)

        # Parse for range -> for(int a:v) {...}
        elif ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            parent_node = self.nh.handle_for_range(ast_item, parent_node)

        # Parse cast expressions -> (int) a
        elif ast_item.kind == CursorKind.CSTYLE_CAST_EXPR:
            parent_node = self.nh.handle_cast_expr(ast_item, parent_node)

        # if not one of the above -> create simple parent node of the kind of the item
        elif ast_item.kind != CursorKind.TYPE_REF:
            parent_node = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        # Do not iterate through children that we have already treated as arguments
        arguments = []
        if utils.is_call_expr(ast_item):
            arguments = [c.spelling for c in ast_item.get_arguments()]


        # Already handled first child of for range statement, so start from second child
        if ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            for index, child in enumerate(list(ast_item.get_children())[1:]):
                # Add compound statment -> {...} if this is missing
                if index == len(list(ast_item.get_children())[1:]) - 1 and child.kind != CursorKind.COMPOUND_STMT:
                    compound_stmt = Node(self.res_tn.get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt, program)
                else:
                    self.parse_item(child, parent_node, program)

        # Handle one liner if/while statements with no compound statement (={..}) as children -> if (...) return x; ADD COMPOUND STATEMENT ANYWAY
        elif (ast_item.kind == CursorKind.IF_STMT or ast_item.kind == CursorKind.WHILE_STMT)\
             and any(CursorKind.COMPOUND_STMT != child.kind for child in list(ast_item.get_children())[1:]):
            for index, child in enumerate(ast_item.get_children()):
                if (index != 1 and index < len(list(ast_item.get_children())) - 1) or child.kind == CursorKind.COMPOUND_STMT or child.kind == CursorKind.IF_STMT:
                    self.parse_item(child, parent_node, program)
                else:
                    compound_stmt = Node(self.res_tn.get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt, program)

        # Handle for statements with no compound statement. ADD COMPOUND STATEMENT
        elif (ast_item.kind == CursorKind.FOR_STMT or ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT) and list(ast_item.get_children())[-1].kind != CursorKind.COMPOUND_STMT:
            compound_stmt = None
            for index, child in enumerate(ast_item.get_children()):
                if index < len(list(ast_item.get_children())) - 1 or child.kind == CursorKind.COMPOUND_STMT:
                    self.parse_item(child, parent_node, program)
                else:
                    if compound_stmt is None:
                        compound_stmt = Node(self.res_tn.get_token('COMPOUND_STMT'), is_reserved=True, parent=parent_node)
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
                if not(child.kind == CursorKind.PARM_DECL or child.spelling in arguments \
                    or (ast_item.kind == CursorKind.STRUCT_DECL 
                    and self.res_tn.get_label(parent_node.token) == 'DECLARATOR') \
                    or (parent_node and parent_node.token
                    and self.res_tn.get_label(parent_node.token) == 'CONSTRUCTOR'
                    and child.kind != CursorKind.COMPOUND_STMT)):
                    self.parse_item(child, parent_node, program)


    def thread_parser(self, file_queue, pbar, thread_nr):
        while True:
            # Get a program from the queue
            program_id, code, imports = file_queue.get()
            # try:
                # Parse the AST tree for the program
            ast = self.parse_ast(code, imports, thread_nr)
            # except Exception as e:
            #     print(f'Skipping file due to parsing failing: {program_id} - {e}')
            #     pbar.update()
            #     file_queue.task_done()
            #     continue

            # Write the AST tree to file
            with open(f'{self.output_folder}{program_id}.json', 'w') as file:
                file.write(self.exporter.export(ast))

            # Mark as done    
            pbar.update()
            file_queue.task_done()

    def clear_temp_files(self):
        for i in range(multiprocessing.cpu_count()):
            os.remove(f'tmp{i}.cpp')


    def parse_csv(self):
        print('Parsing programs ...')

        # Work with threads to increase the speed
        max_task = multiprocessing.cpu_count()

        # Create output directory if it does not exist yet
        os.makedirs(self.output_folder, exist_ok=True)

        # Read csv file in chunks (may be very large)
        programs = pd.read_csv(self.csv_file_path, chunksize=5e5)

        # iterate over the chunks
        for programs_chunk in programs:
            # Create progressbar
            pbar = tqdm(total=len(programs_chunk))
            # Create file queue to store the program data
            file_queue = queue.Queue(max_task)

            try:
                # Create threads which parse ASTs
                for thread_nr in range(max_task):
                    t = threading.Thread(target=self.thread_parser,
                                        args=(file_queue, pbar, thread_nr))
                    t.daemon = True
                    t.start()

                # Fill the queue with files.
                for program in list(programs_chunk[['solutionId', 'solution', 'imports']].iterrows())[:10]:
                    # if program[1]['solutionId'] == 106395892:
                        file_queue.put((program[1]['solutionId'], program[1]['solution'], program[1]['imports']))

                # Wait for all threads to be done.
                file_queue.join()

                # Clear the temporary files
                self.clear_temp_files()
                self.res_tn.save()
                self.tn.save()

            # Exit program with keyboard interrupt
            except KeyboardInterrupt:
                os.kill(0, 9)




    



