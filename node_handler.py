import utils
from clang.cindex import CursorKind, AccessSpecifier, TypeKind
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
    identifier = Node('IDENTIFIER', is_reserved=True, parent=typedef_decl)
    # Set value of IDENTIFIER to spelling of node
    Node(ast_item.spelling, is_reserved=False, parent=identifier)


def handle_declaration(ast_item, parent_node, parse_item): 
    if utils.is_function(ast_item):
        if (ast_item.kind == CursorKind.FUNCTION_TEMPLATE):
            template_decl = Node('TEMPLATE_DECL', is_reserved=True, parent=parent_node)
            for child in ast_item.get_children():
                if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                    templ_param = Node(child.kind.name, is_reserved=True, parent=template_decl)
                    Node(child.spelling, is_reserved=False, parent=templ_param)

        
        func_decl = Node('FUNCTION_DECL', is_reserved=True, parent=parent_node)

        if ast_item.access_specifier != AccessSpecifier.INVALID:
            acc_spec = Node('ACCESS_SPECIFIER', is_reserved=True, parent=func_decl)
            Node(ast_item.access_specifier.name, is_reserved=True, parent=acc_spec)


        name = Node('NAME', is_reserved=True, parent=func_decl)
        Node(ast_item.spelling, is_reserved=False, parent=name)
        if ast_item.kind != CursorKind.CONSTRUCTOR:
            return_type = Node('RETURN_TYPE', is_reserved=True, parent=func_decl)
            Node(ast_item.type.get_result().spelling, is_reserved=False, parent=return_type)

        if ast_item.is_const_method():
            Node('CONST', is_reserved=True, parent=func_decl)


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
                reference = Node('NAME', is_reserved=True, parent=declarator)
                Node(child.spelling, is_reserved=False, parent=reference)

                for c in child.get_children():
                    parse_item(c, declarator)

        return func_decl
    elif utils.is_class(ast_item):
        class_decl = Node('CLASS_DECL', is_reserved=True, parent=parent_node)
        name = Node('NAME', is_reserved=True, parent=class_decl)
        Node(ast_item.spelling, is_reserved=False, parent=name)
        cmpnd_stmt = Node('COMPOUND_STMT', is_reserved=True, parent=class_decl)

        return cmpnd_stmt
    elif ast_item.kind == CursorKind.VAR_DECL or ast_item.kind == CursorKind.FIELD_DECL or ast_item.kind == CursorKind.UNEXPOSED_DECL:
        var_decl = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

        if ast_item.access_specifier != AccessSpecifier.INVALID and ast_item.kind == CursorKind.FIELD_DECL:
            acc_spec = Node('ACCESS_SPECIFIER', is_reserved=True, parent=var_decl)
            Node(ast_item.access_specifier.name, is_reserved=True, parent=acc_spec)

        type_node = Node('TYPE', is_reserved=True, parent=var_decl)
        # unexposed declarations get type auto
        if ast_item.kind == CursorKind.UNEXPOSED_DECL:
            Node('auto', is_reserved=False, parent=type_node)
        else:
            Node(ast_item.type.spelling, is_reserved=False, parent=type_node)
        declarator = Node('DECLARATOR', is_reserved=True, parent=var_decl)
        reference = Node('NAME', is_reserved=True, parent=declarator)
        Node(ast_item.spelling, is_reserved=False, parent=reference)

        # print(ast_item.spelling, ast_item.kind.name)
        # print([(c.spelling, c.kind.name) for c in ast_item.get_children()])
        # for child in ast_item.get_children():
        #     print([(c.spelling, c.kind.name) for c in child.get_children()])
        return declarator

    elif utils.is_struct(ast_item):
        # If parent is declarator we are declaring a structure variable so we
        # do not want to declare the enitre structure again
        if parent_node.label != 'DECLARATOR':
            class_decl = Node('STRUCT_DECL', is_reserved=True, parent=parent_node)
            name = Node('NAME', is_reserved=True, parent=class_decl)
            Node(ast_item.spelling, is_reserved=False, parent=name)
            cmpnd_stmt = Node('COMPOUND_STMT', is_reserved=True, parent=class_decl)

            return cmpnd_stmt

        return parent_node


def handle_operator(ast_item, parent_node):
    if ast_item.kind == CursorKind.BINARY_OPERATOR or ast_item.kind == CursorKind.COMPOUND_ASSIGNMENT_OPERATOR:
        operator_index = len(list(list(ast_item.get_children())[0].get_tokens()))
        op_name = [list(ast_item.get_tokens())[operator_index].spelling]
    else:
        op_name = utils.get_operator(ast_item)
        
    operator = Node(ast_item.kind.name.strip() + '_' + '_'.join(op_name), is_reserved=True, parent=parent_node)

    return operator


def handle_literal(ast_item, parent_node):
    lit_type = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

    token = next(ast_item.get_tokens(), None)
    if token:                
        Node(token.spelling, is_reserved=False, parent=lit_type)
    else:
        filename = ast_item.location.file.name
        with open(filename, 'r') as fh:
            contents = fh.read()
        lit = contents[ast_item.extent.start.offset: ast_item.extent.end.offset]
        Node(lit, is_reserved=False, parent=lit_type)


def handle_call_expr(ast_item, parent_node, parse_item):
    func_name = None
    # print(ast_item.spelling, ast_item.kind.name)
    # print(ast_item.referenced.referenced.type.spelling)


    # if not ast_item.referenced:
    #     for child in ast_item.get_children():
    #         if child.type.kind == TypeKind.OVERLOAD:
    #             func_name = list(child.get_children())[0].spelling

    #     if not func_name:    
            # func_node = utils.func_from_pointer(list(ast_item.get_children())[0])
            # func_name = func_node.spelling
            # print(list(ast_item.get_children())[0].type.spelling, list(ast_item.get_children())[0].kind.name)
            # print(func_name, func_node.kind.name, func_node.type.spelling)
            # print([(c.spelling, c.kind.name, c.type.kind) for c in ast_item.get_children()])
            # for child in ast_item.get_children():
            #     print([(c.spelling, c.kind.name, c.type.spelling) for c in child.get_children()])

    # print('-----------------------')
    if ast_item.referenced:        
        if 'struct ' in ast_item.type.spelling:
            return parent_node
        func_name = ast_item.referenced.spelling
    else:
        for child in ast_item.get_children():
            if child.type.kind == TypeKind.OVERLOAD:
                func_node = list(child.get_children())[0]
                func_name = func_node.spelling
                break

        if not func_name:    
            return parent_node
            # pointer to function
            # func_node = utils.func_from_pointer(list(ast_item.get_children())[0])
            # func_name = func_node.spelling

    if not func_name:
        func_name = "FUNCTION_CALL"

    func_name = re.sub(r'\s+|,+', '', func_name)

    special_call_expr = ['vector', 'unordered_map', 'set', 'pair', 'map', 'queue', 'greater', 'priority_queue', 'bitset']

    if func_name in special_call_expr and len(list(ast_item.get_children())) == 0:
        return parent_node
    else:
        func_call = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
        ref = Node('NAME', is_reserved=True, parent=func_call)

        if len(list(ast_item.get_arguments())) > 0 :
            arg_node =  Node('ARGUMENTS', is_reserved=True, parent=func_call)
            
        for arg_item in ast_item.get_arguments():
            parse_item(arg_item, arg_node)

        if func_name in special_call_expr \
        or ast_item.referenced.kind == CursorKind.CONSTRUCTOR and len(list(ast_item.get_children())) > 0:
            # Do not call expressions with const before it
            item_type = ast_item.type.spelling.replace('const', '')
            Node(item_type, is_reserved=False, parent=ref)
            return Node('ARGUMENTS', is_reserved=True, parent=func_call)
        else:
            Node(func_name, is_reserved=False, parent=ref)


        if '::' in [t.spelling for t in ast_item.get_tokens()]:

            # Get deepest child of ast_item
            child = ast_item
            while len(list(child.get_children())):
                child = list(child.get_children())[0]

            # if deepest child is not type_ref, then we have to add it manually
            if child.kind != CursorKind.TYPE_REF:
                type_ref = ''
                for token in ast_item.get_tokens():
                    if token.spelling == '::':
                        break
                    else:
                        type_ref += token.spelling

                type_ref_node = Node('TYPE_REF', is_reserved=True, parent=func_call)
                Node(type_ref, is_reserved=False, parent=type_ref_node)


        return func_call
        


def handle_reference(ast_item, parent_node):
    # print(ast_item.spelling, [node.label for node in parent_node.children])
    # Ignore references to function calls as this has already been defined as the parent node
    parent_func_name = [n.children[0].label for n in parent_node.children if n.label == 'NAME' and parent_node.label != 'DECLARATOR']
    if ast_item.spelling \
    and ast_item.spelling not in parent_func_name:


        is_reserved = True
        reference = Node(ast_item.kind.name, is_reserved, parent=parent_node)
        return Node(ast_item.spelling, False, parent=reference)


def handle_type_ref(ast_item, parent_node):
    type_ref = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)
    Node(ast_item.type.spelling, is_reserved=False, parent=type_ref)

def handle_for_range(ast_item, parent_node):
    stmt = Node(ast_item.kind.name, is_reserved=True, parent=parent_node)

    # Handle first child that is always a variable declaration
    first_child = next(ast_item.get_children())
    var_decl = Node(first_child.kind.name, is_reserved=True, parent=stmt)
    type_node = Node('TYPE', is_reserved=True, parent=var_decl)
    Node(first_child.type.spelling, is_reserved=False, parent=type_node)
    declarator = Node('DECLARATOR', is_reserved=True, parent=var_decl)
    reference = Node('NAME', is_reserved=True, parent=declarator)
    Node(first_child.spelling, is_reserved=False, parent=reference)

    return stmt    

    # print(ast_item.spelling, ast_item.kind.name)
    # print([(c.spelling, c.kind.name) for c in ast_item.get_children()])
