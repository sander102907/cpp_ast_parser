import utils
from clang.cindex import CursorKind
from tree_node import Node
import re

def handle_typedef(ast_item, parent_node):
    # Set top node as TYPEDEF_DECL
    typedef_decl = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
    # Set first child als TYPE_DEF
    type_def = Node('TYPE_DEF',is_reserved=True, parent=typedef_decl)
    # Set value of TYPE def to type of TYPEDEF
    Node(ast_item.underlying_typedef_type.spelling, is_reserved=False, parent=type_def)

    # Set second child as IDENTIFIER
    identifier = Node('INDENTIFIER', is_reserved=True, parent=typedef_decl)
    # Set value of IDENTIFIER to spelling of node
    Node(ast_item.spelling, is_reserved=False, parent=identifier)


def handle_declaration(ast_item, parent_node, parse_item):
    if utils.is_function(ast_item):
        func_decl = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
        Node(ast_item.spelling, is_reserved=False, parent=func_decl)
        return_type = Node('RETURN_TYPE', is_reserved=True, parent=func_decl)
        Node(ast_item.type.get_result().spelling, is_reserved=False, parent=return_type)

        children = ast_item.get_children()
        for child in children:
            parm_declarations = False
            if child.kind == CursorKind.PARM_DECL:
                if not parm_declarations:
                    parm_decl = Node('PARM_DECL', is_reserved=True, parent=func_decl)
                    parm_declarations = True

                type_node = Node('TYPE', is_reserved=True, parent=parm_decl)
                Node(child.type.spelling, is_reserved=False, parent=type_node)
                declarator = Node('DECLARATOR', is_reserved=True, parent=parm_decl)
                reference = Node('REF', is_reserved=True, parent=declarator)
                Node(child.spelling, is_reserved=False, parent=reference)

                for c in child.get_children():
                    self.parse_item(c, declarator)

        return func_decl
    else:
        var_decl = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
        type_node = Node('TYPE', is_reserved=True, parent=var_decl)
        Node(ast_item.type.spelling, is_reserved=False, parent=type_node)
        declarator = Node('DECLARATOR', is_reserved=True, parent=var_decl)
        reference = Node('REF', is_reserved=True, parent=declarator)
        Node(ast_item.spelling, is_reserved=False, parent=reference)

        return declarator


def handle_operator(ast_item, parent_node):
    op_name = utils.get_operator(ast_item)
    operator = Node(ast_item.kind.name.strip() + '_' + '_'.join(op_name), is_reserved=True, parent=parent_node)

    return operator


def handle_literal(ast_item, parent_node):
    lit_type = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

    if ast_item.kind in [CursorKind.STRING_LITERAL, CursorKind.CHARACTER_LITERAL]:
        Node(ast_item.spelling, is_reserved=False, parent=lit_type)
    else:
        token = next(ast_item.get_tokens(), None)
        if token:                
            Node(token.spelling, is_reserved=False, parent=lit_type)


def handle_call_expr(ast_item, parent_node):
    func_name = None
    if ast_item.referenced:
        func_name = ast_item.referenced.spelling
    else:
        # pointer to function
        func_node = utils.func_from_pointer(list(ast_item.get_children())[0])
        func_name = func_node.spelling

    if not func_name:
        func_name = "FUNCTION_CALL"

    func_name = re.sub(r'\s+|,+', '', func_name)


    func_call = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
    return Node(func_name, is_reserved=False, parent=func_call)


def handle_reference(ast_item, parent_node):
    # Ignore references to function calls as this has already been defined as the parent node
    if parent_node.label != ast_item.spelling:
        is_reserved = True
        reference = Node(ast_item.kind.name, is_reserved, parent=parent_node)
        Node(ast_item.spelling, False, parent=reference)


def handle_type_ref(ast_item, parent_node):
    type_ref = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
    Node(ast_item.type.spelling, is_reserved=False, parent=type_ref)
