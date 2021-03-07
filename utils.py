import re
import networkx as nx
import uuid
from clang.cindex import CursorKind, TokenKind


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


def get_id():
    node_id = uuid.uuid1()
    return node_id.int


def add_node(ast_node, parent_node, graph):
    try:
        node_id = ast_node.hash
        kind = ast_node.kind.name
        node = None
        # skip meaningless AST primitives
        if ast_node.kind == CursorKind.DECL_STMT or \
           ast_node.kind == CursorKind.UNEXPOSED_EXPR:
            return None

        if is_operator(ast_node):
            op_name = get_operator(ast_node)
            kind = kind.strip() + "_" + "_".join(op_name)

        graph.add_node(node_id, label=kind, is_reserved=True)            

        # print("Cursor kind : {0}".format(kind))
        if ast_node.kind.is_declaration():
            node = add_declaration(node_id, ast_node, parent_node, graph)
        elif is_literal(ast_node):
            node = add_literal(node_id, ast_node, parent_node, graph)
        elif is_reference(ast_node):
            node = add_reference(node_id, ast_node, parent_node, graph)
        elif is_call_expr(ast_node):
            node = add_call_expr(node_id, ast_node, parent_node, graph)
            
        if parent_node is not None:
            node = Node(kind, True, parent=parent_node)

        return node
    except Exception as e:
        if 'Unknown template argument kind' not in str(e):
            msg = make_ast_err_message(str(e), ast_node)
            raise Exception(msg)


def add_child(graph, parent_id, parent_node, name, is_reserved=True):
    child_id = get_id()
    assert len(name) > 0, "Missing node name"
    graph.add_node(child_id, label=name, is_reserved=is_reserved)
    graph.add_edge(parent_id, child_id)
    return Node(name, is_reserved, parent=parent_node)


def add_intermediate_node(graph, parent_id, parent_node, name):
    child_id = get_id()
    assert len(name) > 0, "Missing node name"
    graph.add_node(child_id, label=name, is_reserved=True)
    graph.add_edge(parent_id, child_id)
    Node(name, True, parent=parent_node)
    return child_id


def add_call_expr(parent_id, ast_node, parent_node, graph):
    expr_type = ast_node.type.spelling
    expr_type_node_id = add_intermediate_node(graph, parent_id, parent_node, "EXPR_TYPE")
    return add_child(graph, expr_type_node_id, parent_node, expr_type, is_reserved=False)


def fix_cpp_operator_spelling(op_name):
    if op_name == '|':
        return 'OPERATOR_BINARY_OR'
    elif op_name == '||':
        return 'OPERATOR_LOGICAL_OR'
    elif op_name == '|=':
        return 'OPERATOR_ASSIGN_OR'
    elif op_name == ',':
        return 'OPERATOR_COMMA'
    else:
        return op_name


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
                name.append(ch) #fix_cpp_operator_spelling(ch).strip())
        return name
    else:
        name = name_token.spelling
        # name = fix_cpp_operator_spelling(name)
        if name in ['++', '--']:
            if name == list(ast_node.get_tokens())[0].spelling:
                name = 'PRE_' + name
            else:
                name = 'POST_' + name
        return [name.strip()]


def add_reference(parent_id, ast_node, parent_node, graph):
    is_reserved = True
    name = "REFERENCE"
    if ast_node.kind in [CursorKind.DECL_REF_EXPR, CursorKind.MEMBER_REF_EXPR]:
        
        for token in ast_node.get_tokens():
            if token.kind == TokenKind.IDENTIFIER:
                name = token.spelling
                is_reserved = False
                break
    else:
        name = ast_node.spelling
        is_reserved = False

    return add_child(graph, parent_id, parent_node, name, is_reserved)


def add_literal(parent_id, ast_node, parent_node, graph):
    if ast_node.kind in [CursorKind.STRING_LITERAL,
                         CursorKind.CHARACTER_LITERAL]:
        return add_child(graph, parent_id, parent_node, 'STRING_VALUE', is_reserved=True)
    else:
        token = next(ast_node.get_tokens(), None)
        if token:
            value = token.spelling
            return add_child(graph, parent_id, parent_node, value)
            # print("\tValue : {0}".format(value))


def add_declaration(parent_id, ast_node, parent_node, graph):
    is_func = False
    if is_function(ast_node):
        is_func = True
        return_type = ast_node.type.get_result().spelling
        if len(return_type) > 0:
            return_type_node_id = add_intermediate_node(graph, parent_id, parent_node, "RETURN_TYPE")
            return add_child(graph, return_type_node_id, parent_node, return_type, is_reserved=False)
    else:
        declaration_type = ast_node.type.spelling
        if len(declaration_type) > 0:
            declaration_type_node_id = add_intermediate_node(graph, parent_id, parent_node, "DECLARATION_TYPE")
            return add_child(graph, declaration_type_node_id, parent_node, declaration_type, is_reserved=False)

    if not is_template_parameter(ast_node):
        is_reserved = False
        name = ast_node.spelling

        # handle unnamed declarations
        if len(name) == 0:
            name = ast_node.kind.name + "_UNNAMED"
            is_reserved = True

        name_node_id = add_intermediate_node(graph, parent_id, parent_node, "DECLARATION_NAME")

        return add_child(graph, name_node_id, parent_node, name, is_reserved=is_reserved)


def func_from_pointer(ast_node):
    children = list(ast_node.get_children())
    if children:
        return func_from_pointer(children[0])
    else:
        return ast_node


def ast_to_graph(ast_start_node, root_node, max_depth):
    g = nx.Graph()
    stack = [(ast_start_node, 0)]
    parent_map = {ast_start_node.hash: None}
    parent_node_map = {ast_start_node.hash: root_node}
    while stack:
        ast_node, depth = stack.pop()
        node_id = ast_node.hash
        if not g.has_node(node_id):
            parent_id = parent_map[node_id]
            parent_node = parent_node_map[node_id]
            tree_node = add_node(ast_node, parent_node, g)
            if tree_node is not None:
                if parent_id is not None:
                    g.add_edge(parent_id, node_id)

                if is_call_expr(ast_node):
                    func_name = None
                    if ast_node.referenced:
                        func_name = ast_node.referenced.spelling
                    else:
                        # pointer to function
                        func_node = func_from_pointer(list(ast_node.get_children())[0])
                        func_name = func_node.spelling

                    if not func_name:
                        func_name = "FUNCTION_CALL"
                    func_name = re.sub(r'\s+|,+', '', func_name)

                    call_expr_id = add_intermediate_node(g, node_id, parent_node, func_name)
                    node_id = call_expr_id
            else:
                node_id = parent_id

            # Ignore too deep trees
            if max_depth == 0 or depth <= max_depth:
                if is_call_expr(ast_node):
                    for arg_node in ast_node.get_arguments():
                        stack.append((arg_node, depth + 1))
                        parent_map[arg_node.hash] = node_id
                        parent_node_map[arg_node.hash] = tree_node
                else:
                    for child_node in ast_node.get_children():
                        stack.append((child_node, depth + 1))
                        parent_map[child_node.hash] = node_id
                        parent_node_map[child_node.hash] = tree_node
    return g