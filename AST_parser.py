import clang.cindex
from clang.cindex import CursorKind
from anytree import RenderTree
from tree_node import Node
from tidy_files import tidy_file
import utils
from node_handler import *

class AstParser:
    def __init__(self, clang_lib_file='/usr/lib/x86_64-linux-gnu/libclang-6.0.so.1'):
        try:
            clang.cindex.Config.set_library_file(clang_lib_file)
        except Exception as e:
            print(f'Skipped setting library file: {e}')

        self.index = clang.cindex.Index.create()


    def parse_ast(self, input_file_path):
        tidy_file(input_file_path)
        tu = self.index.parse(input_file_path)
        cursor_items = self.get_cursor_items(tu.cursor)
        root_node = Node('root', is_reserved=True)

        for cursor_item in cursor_items:
            self.parse_item(cursor_item, root_node)

        return root_node


    def get_cursor_items(self, cursor):
        cursor_items = []
        user_code_started = False

        for child in cursor.get_children():
            if user_code_started:
                cursor_items.append(child)
            if child.kind == CursorKind.USING_DIRECTIVE:
                user_code_started = True

        return cursor_items


    def parse_item(self, ast_item, parent_node):
        # skip meaningless AST primitives
        if ast_item.kind == CursorKind.DECL_STMT \
        or ast_item.kind == CursorKind.UNEXPOSED_EXPR \
        or ast_item.kind == CursorKind.TEMPLATE_REF \
        or ast_item.kind == CursorKind.NAMESPACE_REF:
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
        elif ast_item.kind == CursorKind.TYPE_REF and parent_node.label != 'root':
            handle_type_ref(ast_item, parent_node)


        # if not one of the above -> create simple parent node of the kind of the item
        elif ast_item.kind != CursorKind.TYPE_REF:
            parent_node = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

        # Do not iterate through children that we have already treated as arguments
        arguments = []
        if utils.is_call_expr(ast_item):
            arguments = [c.spelling for c in ast_item.get_arguments()]

        for child in ast_item.get_children():
            if child.kind != CursorKind.PARM_DECL and child.spelling not in arguments:
                self.parse_item(child, parent_node)


ast_parser = AstParser()
ast = ast_parser.parse_ast('data/subset/cpp/104606100.cpp')

for pre, fill, node in RenderTree(ast):
    treestr = u"%s%s" % (pre, node.label)
    print(treestr)

from anytree.exporter import JsonExporter

exporter = JsonExporter(indent=2)
with open('ast_parser/tree.json', 'w') as file:
    file.write(exporter.export(ast))


