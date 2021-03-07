import os
import clang.cindex
from clang.cindex import CursorKind
from anytree import RenderTree
from tree_node import Node
from tidy_files import add_readability_braces, preprocess_file
import utils
from node_handler import *
from tqdm import tqdm
from anytree.exporter import JsonExporter
import threading
import multiprocessing
import queue as queue
import json

class AstParser:
    def __init__(self, clang_lib_file='/usr/lib/x86_64-linux-gnu/libclang-6.0.so.1'):
        try:
            clang.cindex.Config.set_library_file(clang_lib_file)
        except Exception as e:
            print('Skipped setting library file: {}'.format(e))

        self.index = clang.cindex.Index.create()


    def parse_ast(self, input_file_path):
        # add_readability_braces(input_file_path)
        imports = preprocess_file(input_file_path)
        tu = self.index.parse(input_file_path, args=['-x', 'c++', '-std=c++17'])
        cursor_items = self.get_cursor_items(tu.cursor, input_file_path)
        root_node = Node('root', is_reserved=True)

        # for cursor_item in cursor_items:
        #     for c in cursor_item.walk_preorder():
        #         print(f'spelling: {c.spelling}, kind: {c.kind.name}, type spelling: {c.type.spelling}, return type: {c.type.get_result().spelling}, type kind: {c.type.kind}')

        for cursor_item in cursor_items:
            self.parse_item(cursor_item, root_node)

        return root_node, imports


    def get_cursor_items(self, cursor, input_file_path):
        cursor_items = []
        user_code_started = False

        for child in cursor.get_children():
            if str(child.location.file) == input_file_path:
                cursor_items.append(child)
            # if child.kind == CursorKind.USING_DIRECTIVE:
            #     user_code_started = True

        return cursor_items


    def parse_item(self, ast_item, parent_node):        
        # skip meaningless AST primitives
        skip_kinds = [
            CursorKind.UNEXPOSED_EXPR, CursorKind.OVERLOADED_DECL_REF,
            CursorKind.NAMESPACE_REF, CursorKind.TEMPLATE_REF
            ]

        if ast_item.kind in skip_kinds \
        or 'operatorbool' == ast_item.spelling \
        or 'operator bool' == ast_item.spelling \
        or (('std::string' == ast_item.type.spelling \
        or 'basic_string' == ast_item.spelling) \
        and ast_item.kind in [CursorKind.TYPE_REF, CursorKind.CALL_EXPR]):
            pass

        # Parse typdef
        elif utils.is_typedef(ast_item):
            handle_typedef(ast_item, parent_node)


        # parse declaration
        elif ast_item.kind.is_declaration():
            parent_node = handle_declaration(ast_item, parent_node, self.parse_item)

        # parse operator
        elif utils.is_operator(ast_item):
            parent_node = handle_operator(ast_item, parent_node)

        # parse literal
        elif utils.is_literal(ast_item):
            handle_literal(ast_item, parent_node)


        # parse call expression
        elif utils.is_call_expr(ast_item):
            parent_node = handle_call_expr(ast_item, parent_node, self.parse_item)


        # parse reference
        elif utils.is_reference(ast_item):
            p_node = handle_reference(ast_item, parent_node)

            if p_node:
                parent_node = p_node
        

        # parse type ref
        elif ast_item.kind == CursorKind.TYPE_REF \
            and parent_node and parent_node.label != 'root' \
            and parent_node.label != 'DECLARATOR' \
            and parent_node.label != 'FUNCTION_DECL'\
            and parent_node.label != 'ARGUMENTS':
            handle_type_ref(ast_item, parent_node)

        elif ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            parent_node = handle_for_range(ast_item, parent_node)

        # elif ast_item.kind == CursorKind.OVERLOADED_DECL_REF:
        #     parent_node = Node(ast_item.spelling, is_reserved=True, parent=parent_node)
        #     print(ast_item.spelling, ast_item.kind.name, ast_item.type.spelling)


        # if not one of the above -> create simple parent node of the kind of the item
        elif ast_item.kind != CursorKind.TYPE_REF:
            # print([(c.spelling, c.kind.name) for c in ast_item.get_children()])
            # for child in ast_item.get_children():
            #     print([(c.spelling, c.kind.name) for c in child.get_children()])
            # if ast_item.kind == CursorKind.PAREN_EXPR:
            #     print([(c.spelling, c.kind.name) for c in ast_item.get_children()])
            #     for child in ast_item.get_children():
            #         print([(c.spelling, c.kind.name) for c in child.get_children()])
            parent_node = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

        # Do not iterate through children that we have already treated as arguments
        arguments = []
        if utils.is_call_expr(ast_item):
            arguments = [c.spelling for c in ast_item.get_arguments()]
        # Already handled first child of for range statement, so start from second child
        if ast_item.kind == CursorKind.CXX_FOR_RANGE_STMT:
            for child in list(ast_item.get_children())[1:]:
                self.parse_item(child, parent_node)
        # Handle one liner if statements with no compound statement (={..}) as children -> if (...) return x; ADD COMPOUND STATEMENT ANYWAY
        elif ast_item.kind == CursorKind.IF_STMT and CursorKind.COMPOUND_STMT != list(ast_item.get_children())[1].kind:
            compound_stmt = None
            for index, child in enumerate(ast_item.get_children()):
                if index == 0 or child.kind == CursorKind.COMPOUND_STMT:
                    self.parse_item(child, parent_node)
                else:
                    if compound_stmt is None:
                        compound_stmt = Node('COMPOUND_STMT', is_reserved=True, parent=parent_node)
                    self.parse_item(child, compound_stmt)

        else:
            for child in ast_item.get_children():
                if not(child.kind == CursorKind.PARM_DECL or child.spelling in arguments \
                    or (ast_item.kind == CursorKind.STRUCT_DECL and parent_node.label == 'DECLARATOR')):
                        self.parse_item(child, parent_node)



ast_parser = AstParser()
exporter = JsonExporter(indent=2)


def thread_parser(file_paths, pbar, output_folder, imports_data):
    while True:
        file_path = file_queue.get()
        try:
            ast, imports = ast_parser.parse_ast(file_path)
        except RuntimeError:
            print(f'Skipping file due to error in the source code: {file_path}')   
            pbar.update() 
            file_queue.task_done()
            continue
        except Exception as e:
            print(f'Skipping file due to parsing failing: {file_path} - {e}')
            pbar.update()
            file_queue.task_done()
            continue

        file_name = file_path.split('/')[-1]

        with open(f'{output_folder}{file_name.split(".")[0]}.json', 'w') as file:
            file.write(exporter.export(ast))

        imports_data.put({file_name.split(".")[0]: imports})
                
        pbar.update()
        file_queue.task_done()

# Work with threads to increase the speed
max_task = multiprocessing.cpu_count()
file_paths = []
input_folder = '../data/subset/cpp_preprocessed/'
output_folder = '../data/subset/ast_trees/'

imports_data = multiprocessing.Queue()


for dirs,_,files in os.walk(input_folder):
    # Create folder to save data if it does not exist yet
    os.makedirs(f'{output_folder}{dirs}', exist_ok=True)
    for f in files:
    	file_paths.append(dirs + f)
 
pbar = tqdm(total=len(file_paths))
file_queue = queue.Queue(max_task)

try:
    for _ in range(max_task):
        t = threading.Thread(target=thread_parser,
                            args=(file_queue, pbar, output_folder, imports_data))
        t.daemon = True
        t.start()

    # Fill the queue with files.
    for f in file_paths:
        file_queue.put(f)

    # Wait for all threads to be done.
    file_queue.join()

    imports = {}
    
    while not imports_data.empty():
        imports.update(imports_data.get())

    with open('imports.json', 'w') as fout:
        json.dump(imports, fout)

except KeyboardInterrupt:
    os.kill(0, 9)




    



