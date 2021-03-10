import utils
from clang.cindex import CursorKind, AccessSpecifier, TypeKind
from tree_node import Node
import re

class NodeHandler:
    def __init__(self, res_tn, tn):
        # Set reserved label and non reserved label tokenizers
        self.res_tn = res_tn
        self.tn = tn

    def handle_typedef(self, ast_item, parent_node):
        # Set top node as TYPEDEF_DECL
        typedef_decl = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        # Set first child als TYPE_DEF
        type_def = Node(self.res_tn.get_token('TYPE_DEF'),is_reserved=True, parent=typedef_decl)
        # Set value of TYPE def to type of TYPEDEF
        Node(self.tn.get_token(ast_item.underlying_typedef_type.spelling), is_reserved=False, parent=type_def)

        # Set second child as IDENTIFIER
        identifier = Node(self.res_tn.get_token('IDENTIFIER'), is_reserved=True, parent=typedef_decl)
        # Set value of IDENTIFIER to spelling of node
        Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=identifier)


    def handle_declaration(self, ast_item, parent_node, parse_item, program): 
        if utils.is_function(ast_item):
            if (ast_item.kind == CursorKind.FUNCTION_TEMPLATE):
                template_decl = Node(self.res_tn.get_token('TEMPLATE_DECL'), is_reserved=True, parent=parent_node)
                for child in ast_item.get_children():
                    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                        templ_param = Node(self.res_tn.get_token(child.kind.name), is_reserved=True, parent=template_decl)
                        Node(self.tn.get_token(child.spelling), is_reserved=False, parent=templ_param)

            
            func_decl = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID:
                acc_spec = Node(self.res_tn.get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=func_decl)
                Node(self.res_tn.get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)


            name = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=func_decl)
            Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
            if ast_item.kind != CursorKind.CONSTRUCTOR:
                return_type = Node(self.res_tn.get_token('RETURN_TYPE'), is_reserved=True, parent=func_decl)
                Node(self.tn.get_token(ast_item.type.get_result().spelling), is_reserved=False, parent=return_type)

            if ast_item.is_const_method():
                Node(self.res_tn.get_token('CONST'), is_reserved=True, parent=func_decl)


            children = ast_item.get_children()
            for child in children:
                parm_declarations = False
                if child.kind == CursorKind.PARM_DECL:
                    if not parm_declarations:
                        parm_decl = Node(self.res_tn.get_token('PARM_DECL'), is_reserved=True, parent=func_decl)
                        parm_declarations = True

                    type_node = Node(self.res_tn.get_token('TYPE'), is_reserved=True, parent=parm_decl)
                    Node(self.tn.get_token(child.type.spelling), is_reserved=False, parent=type_node)
                    declarator = Node(self.res_tn.get_token('DECLARATOR'), is_reserved=True, parent=parm_decl)
                    reference = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=declarator)
                    Node(self.tn.get_token(child.spelling), is_reserved=False, parent=reference)

                    for c in child.get_children():
                        parse_item(c, declarator, program)

            # Get children of constructor which are not parameters or compount statements, thus are constructor initializers
            if ast_item.kind == CursorKind.CONSTRUCTOR:
                constructor_inits = [child for child in ast_item.get_children() if child.kind != CursorKind.COMPOUND_STMT and child.kind != CursorKind.PARM_DECL]
                for i in range(0,len(constructor_inits), 2):
                    constr_init = Node(self.res_tn.get_token('CONSTRUCTOR_INITIALIZER'), is_reserved=True, parent=func_decl)

                    member_ref = Node(self.res_tn.get_token(constructor_inits[i].kind.name), is_reserved=True, parent=constr_init)
                    Node(self.tn.get_token(constructor_inits[i].spelling), is_reserved=False, parent=member_ref)

                    parse_item(constructor_inits[i + 1], constr_init, program)                

            return func_decl

        elif utils.is_class(ast_item):
            class_decl = Node(self.res_tn.get_token('CLASS_DECL'), is_reserved=True, parent=parent_node)
            name = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=class_decl)
            Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
            cmpnd_stmt = Node(self.res_tn.get_token('COMPOUND_STMT'), is_reserved=True, parent=class_decl)

            return cmpnd_stmt
        elif ast_item.kind == CursorKind.VAR_DECL or ast_item.kind == CursorKind.FIELD_DECL or ast_item.kind == CursorKind.UNEXPOSED_DECL:
            var_decl = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID and ast_item.kind == CursorKind.FIELD_DECL:
                acc_spec = Node(self.res_tn.get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=var_decl)
                Node(self.res_tn.get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)

            type_node = Node(self.res_tn.get_token('TYPE'), is_reserved=True, parent=var_decl)
            # unexposed declarations get type auto
            if ast_item.kind == CursorKind.UNEXPOSED_DECL:
                Node(self.tn.get_token('auto'), is_reserved=False, parent=type_node)
            else:
                Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=type_node)
            declarator = Node(self.res_tn.get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
            reference = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=declarator)
            Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=reference)

            return declarator

        elif utils.is_struct(ast_item):
            # If parent is declarator we are declaring a structure variable so we
            # do not want to declare the enitre structure again
            if self.res_tn.get_label(parent_node.token) != 'DECLARATOR':
                class_decl = Node(self.res_tn.get_token('STRUCT_DECL'), is_reserved=True, parent=parent_node)
                name = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=class_decl)
                Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
                cmpnd_stmt = Node(self.res_tn.get_token('COMPOUND_STMT'), is_reserved=True, parent=class_decl)

                return cmpnd_stmt

            return parent_node


    def handle_operator(self, ast_item, parent_node):
        if ast_item.kind == CursorKind.BINARY_OPERATOR or ast_item.kind == CursorKind.COMPOUND_ASSIGNMENT_OPERATOR:
            try:
                operator_index = len(list(list(ast_item.get_children())[0].get_tokens()))
                op_name = [list(ast_item.get_tokens())[operator_index].spelling]
            except IndexError:
                len_first_child = len([t.spelling for t in list(ast_item.get_children())[0].get_tokens()])
                len_second_child = len([t.spelling for t in list(ast_item.get_children())[1].get_tokens()])
                operator_index = len_first_child - len_second_child - 1
                try:
                    op_name = [list(ast_item.get_tokens())[operator_index].spelling]
                except IndexError:
                    op_name = [[t.spelling for t in list(ast_item.get_children())[1].get_tokens()][0]]

        elif ast_item.kind == CursorKind.UNARY_OPERATOR:
            tokens = list(ast_item.get_tokens())
            if utils.is_operator_token(tokens[0].spelling):
                op_name = tokens[0].spelling
                if op_name in ['++', '--']:
                    op_name = 'PRE_' + op_name
            else:
                op_name = tokens[-1].spelling
                if op_name in ['++', '--']:
                    op_name = 'POST_' + op_name

            op_name = [op_name]

        else:
            op_name = utils.get_operator(ast_item)
            
        operator = Node(self.res_tn.get_token(ast_item.kind.name.strip() + '_' + '_'.join(op_name)), is_reserved=True, parent=parent_node)

        return operator


    def handle_literal(self, ast_item, parent_node, program):
        lit_type = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        token = next(ast_item.get_tokens(), None)
        if token:                
            Node(self.tn.get_token(token.spelling), is_reserved=False, parent=lit_type)
        else:
            lit = program[ast_item.extent.start.offset: ast_item.extent.end.offset]
            Node(self.tn.get_token(lit), is_reserved=False, parent=lit_type)


    def handle_call_expr(self, ast_item, parent_node, parse_item, program):
        func_name = None

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


        if not func_name:
            func_name = "FUNCTION_CALL"

        func_name = re.sub(r'\s+|,+', '', func_name)

        # Check for pre and post if we have ++ and -- operators
        if func_name in ['operator++', 'operator--']:
            tokens = [t.spelling for t in ast_item.get_tokens()]
            if '++' == tokens[0] or '-' == tokens[0]:
                func_name += '_PRE'
            else:
                func_name += '_POST'

        special_call_expr = ['vector', 'unordered_map', 'set', 'pair', 'map', 'queue', 'greater', 'priority_queue', 'bitset']

        if func_name in special_call_expr and len(list(ast_item.get_children())) == 0:
            return parent_node
        else:
            func_call = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
            ref = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=func_call)

            if len(list(ast_item.get_arguments())) > 0 :
                arg_node =  Node(self.res_tn.get_token('ARGUMENTS'), is_reserved=True, parent=func_call)
                
            for arg_item in ast_item.get_arguments():
                parse_item(arg_item, arg_node, program)

            if func_name in special_call_expr \
            or (ast_item.referenced and ast_item.referenced.kind == CursorKind.CONSTRUCTOR and len(list(ast_item.get_children())) > 0):
                # Do not call expressions with const before it
                item_type = ast_item.type.spelling.replace('const', '')
                Node(self.tn.get_token(item_type), is_reserved=False, parent=ref)
                return Node(self.res_tn.get_token('ARGUMENTS'), is_reserved=True, parent=func_call)
            else:
                Node(self.tn.get_token(func_name), is_reserved=False, parent=ref)


            if '::' in [t.spelling for t in ast_item.get_tokens()]:

                # Check if there is a already a type ref child
                type_ref_child = False
                for child in ast_item.walk_preorder():
                    if child.kind == CursorKind.TYPE_REF:
                        type_ref_child = True
                        break

                # if there is no child of kind type_ref, then we have to add it manually
                if not type_ref_child:
                    type_ref = ''
                    for token in ast_item.get_tokens():
                        if token.spelling == '::':
                            break
                        else:
                            type_ref += token.spelling

                    type_ref_node = Node(self.res_tn.get_token('TYPE_REF'), is_reserved=True, parent=func_call)
                    Node(self.tn.get_token(type_ref), is_reserved=False, parent=type_ref_node)


            return func_call
            


    def handle_reference(self, ast_item, parent_node):
        parent_func_name = [self.res_tn.get_label(n.children[0].token) if n.children[0].res else self.tn.get_label(n.children[0].token)
                            for n in parent_node.children
                            if self.res_tn.get_label(n.token) == 'NAME' and self.res_tn.get_label(parent_node.token) != 'DECLARATOR']
        if ast_item.spelling \
        and ast_item.spelling not in parent_func_name:


            reference = Node(self.res_tn.get_token(ast_item.kind.name), True, parent=parent_node)
            return Node(self.tn.get_token(ast_item.spelling), False, parent=reference)


    def handle_type_ref(self, ast_item, parent_node):
        type_ref = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=type_ref)

    def handle_for_range(self, ast_item, parent_node):
        stmt = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        # Handle first child that is always a variable declaration
        first_child = next(ast_item.get_children())
        var_decl = Node(self.res_tn.get_token(first_child.kind.name), is_reserved=True, parent=stmt)
        type_node = Node(self.res_tn.get_token('TYPE'), is_reserved=True, parent=var_decl)
        Node(self.tn.get_token(first_child.type.spelling), is_reserved=False, parent=type_node)
        declarator = Node(self.res_tn.get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
        reference = Node(self.res_tn.get_token('NAME'), is_reserved=True, parent=declarator)
        Node(self.tn.get_token(first_child.spelling), is_reserved=False, parent=reference)

        return stmt    


    def handle_cast_expr(self, ast_item, parent_node):
        cast_expr = Node(self.res_tn.get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        if not CursorKind.TYPE_REF in [c.kind for c in ast_item.get_children()]:
            cast_type = Node(self.res_tn.get_token('TYPE'), is_reserved=True, parent=cast_expr)
            Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=cast_type)
        return cast_expr