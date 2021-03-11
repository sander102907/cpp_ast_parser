import re
import networkx as nx
import uuid
from clang.cindex import CursorKind, TokenKind
import os


def is_node_kind_safe(node, kinds):
    try:
        return node.kind in kinds
    except Exception as e:
        msg = make_ast_err_message(str(e), node)
        if 'Unknown template argument kind' not in str(e):
            print(msg)
        return CursorKind.NOT_IMPLEMENTED


def is_namespace(node):
    if is_node_kind_safe(node, [CursorKind.NAMESPACE]):
        return True
    return False


def is_function(node):
    if is_node_kind_safe(node, 
    [CursorKind.FUNCTION_DECL,
     CursorKind.FUNCTION_TEMPLATE,
     CursorKind.CXX_METHOD,
     CursorKind.DESTRUCTOR, 
     CursorKind.CONSTRUCTOR]): # and node.is_definition(): <- TEST IF THIS CAN BE REMOVED WITHOUT ISSUES
            not_empty = False
            for _ in node.get_children():
                not_empty = True
                break
            return not_empty
    return False


def is_class(node):
    return is_node_kind_safe(node, [CursorKind.CLASS_TEMPLATE,
                                    CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
                                    CursorKind.CLASS_DECL])

def is_struct(node):
    return is_node_kind_safe(node, [CursorKind.STRUCT_DECL])


def is_literal(node):
    return is_node_kind_safe(node, [CursorKind.INTEGER_LITERAL,
                                    CursorKind.FLOATING_LITERAL,
                                    CursorKind.IMAGINARY_LITERAL,
                                    CursorKind.STRING_LITERAL,
                                    CursorKind.CHARACTER_LITERAL,
                                    CursorKind.CXX_BOOL_LITERAL_EXPR])


def is_template_parameter(node):
    return is_node_kind_safe(node, [CursorKind.TEMPLATE_TYPE_PARAMETER,
                                    CursorKind.TEMPLATE_TEMPLATE_PARAMETER])


def is_reference(node):
    return is_node_kind_safe(node, [CursorKind.DECL_REF_EXPR, CursorKind.MEMBER_REF_EXPR])


def is_operator(node):
    return is_node_kind_safe(node, [CursorKind.BINARY_OPERATOR,
                                    CursorKind.UNARY_OPERATOR,
                                    CursorKind.COMPOUND_ASSIGNMENT_OPERATOR,
                                    CursorKind.CXX_UNARY_EXPR])

def is_typedef(node):
    return is_node_kind_safe(node, [CursorKind.TYPEDEF_DECL])


def is_call_expr(node):
    return is_node_kind_safe(node, [CursorKind.CALL_EXPR])


binary_operators = ['+', '-', '*', '/', '%', '&', '|', '>>']
unary_operators = ['++', '--', '!', 'sizeof', 'addressof']
comparison_operators = ['==', '<=', '>=', '<', '>', '!=', '&&', '||']
unary_assignment_operators = [op + '=' for op in binary_operators]
assignment_operators = ['='] + unary_assignment_operators
misc_operators = [',']


def is_operator_token(token):
    if token in binary_operators:
        return True
    if token in unary_operators:
        return True
    if token in comparison_operators:
        return True
    if token in unary_assignment_operators:
        return True
    if token in assignment_operators:
        return True
    if token in misc_operators:
        return True


def get_operator(ast_node):
    name_token = None
    assignment_operator = False
    operator_tokens = [token for token in ast_node.get_tokens() if is_operator_token(token.spelling)]
    for operator_token in operator_tokens:
        if operator_token.spelling in assignment_operators:
            assignment_operator = True
            name_token = operator_token 
    
    if len(operator_tokens) > 0 and assignment_operator == False:
        name_token = operator_tokens[-1]

    if not name_token:
        filename = ast_node.location.file.name
        with open(filename, 'r') as fh:
            contents = fh.read()
        code_str = contents[ast_node.extent.start.offset: ast_node.extent.end.offset]
        name = []
        for ch in code_str:
            if ch in binary_operators:
                name.append(ch)
        return name
    else:
        name = name_token.spelling
        if name in ['++', '--']:
            if name == list(ast_node.get_tokens())[0].spelling:
                name = 'PRE_' + name
            else:
                name = 'POST_' + name
        return [name.strip()]


def add_includes_usings(file, includes_usings):
    new_file_name = '/'.join(file.split('/')[:-1]) + 'preprocessed_' + file.split('/')[-1]
    with open(file) as f, open(new_file_name, "w") as new_f:
        code = f.read()

        for element in includes_usings:
            new_f.write(f'{element}\n')

        new_f.write('\n')
        new_f.write(code)

    # remove original file
    os.remove(file)
    # Rename dummy file as the original file
    os.rename(new_file_name, file)
