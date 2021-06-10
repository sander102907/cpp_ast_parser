import utils
import clang.cindex
from clang.cindex import CursorKind, AccessSpecifier, TypeKind, TokenKind
from tree_node import Node
import re

class NodeHandler:
    def __init__(self, tokenizers, split_terminals, cindex):
        # Set reserved label and non reserved label tokenizers
        self.tokenizers = tokenizers
        self.split_terminals = split_terminals

        self.cindex = cindex

        self.builtin_types = ['int', 'long', 'long long', 'double', 'long double', 'unsigned long long', 'vector',
                            'void', 'map', 'auto', 'short', 'deque', 'bool', 'pair', 'int32_t', 'queue', 'priority_queue',
                            'istream_iterator', 'complex', 'char', 'set', 'unsigned int', 'string', 'stack', 'unordered_map',
                            'tuple', 'multiset', 'unsigned long', 'unsigned char', 'signed char', 'signed int', 'short int',
                            'unsigned short int', 'signed short int', 'long int', 'signed long int', 'unsigned long int', 'long long int',
                            'unsigned long long int', 'float', 'wchar_t', 'bitset', 'unordered_set', 'basic_string', 'array', 'forward_list',
                            'shared_ptr', '__cxx11::basic_string', 'basic_string', 'string', 'allocator', 'less']
                            

    def handle_typedef(self, ast_item, parent_node):
        # Set top node as TYPEDEF_DECL
        typedef_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        # Set first child als TYPE_DEF
        type_def = Node(self.tokenizers['RES'].get_token('TYPE_DEF'),is_reserved=True, parent=typedef_decl)
        
        self.handle_type(ast_item, type_def)

        # Set second child as IDENTIFIER
        identifier = Node(self.tokenizers['RES'].get_token('IDENTIFIER'), is_reserved=True, parent=typedef_decl)
        # Set value of IDENTIFIER to spelling of node
        self.create_terminal_nodes(ast_item.spelling, ast_item, identifier)


    def handle_declaration(self, ast_item, parent_node, parse_item, program): 
        if utils.is_function(ast_item):
            if (ast_item.kind == CursorKind.FUNCTION_TEMPLATE):
                template_decl = Node(self.tokenizers['RES'].get_token('TEMPLATE_DECL'), is_reserved=True, parent=parent_node)
                for child in ast_item.get_children():
                    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                        templ_param = Node(self.tokenizers['RES'].get_token(child.kind.name), is_reserved=True, parent=template_decl)
                        self.create_terminal_nodes(child.spelling, child, templ_param)

            
            func_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID and self.tokenizers['RES'].get_label(parent_node.token) != 'root':
                acc_spec = Node(self.tokenizers['RES'].get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=func_decl)
                Node(self.tokenizers['RES'].get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)


            name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=func_decl)
            self.create_terminal_nodes(ast_item.spelling, ast_item, name)
            # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
            if ast_item.kind != CursorKind.CONSTRUCTOR:
                self.handle_type(ast_item, func_decl)

            if ast_item.is_const_method():
                Node(self.tokenizers['RES'].get_token('CONST'), is_reserved=True, parent=func_decl)


            children = ast_item.get_children()
            for child in children:
                parm_declarations = False
                if child.kind == CursorKind.PARM_DECL:
                    if not parm_declarations:
                        parm_decl = Node(self.tokenizers['RES'].get_token('PARM_DECL'), is_reserved=True, parent=func_decl)
                        parm_declarations = True

                    self.handle_type(child, parm_decl)

                    declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=parm_decl)
                    reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
                    self.create_terminal_nodes(child.spelling, child, reference)

                    for c in child.get_children():
                        parse_item(c, declarator, program)

            # Get children of constructor which are not parameters or compount statements, thus are constructor initializers
            if ast_item.kind == CursorKind.CONSTRUCTOR:
                constructor_inits = [child for child in ast_item.get_children() if child.kind != CursorKind.COMPOUND_STMT and child.kind != CursorKind.PARM_DECL]
                for i in range(0,len(constructor_inits), 2):
                    constr_init = Node(self.tokenizers['RES'].get_token('CONSTRUCTOR_INITIALIZER'), is_reserved=True, parent=func_decl)

                    member_ref = Node(self.tokenizers['RES'].get_token(constructor_inits[i].kind.name), is_reserved=True, parent=constr_init)
                    self.create_terminal_nodes(constructor_inits[i].spelling, constructor_inits[i], member_ref)

                    parse_item(constructor_inits[i + 1], constr_init, program)                

            return func_decl

        elif utils.is_class(ast_item):
            if ast_item.kind == CursorKind.CLASS_TEMPLATE:
                template_decl = Node(self.tokenizers['RES'].get_token('TEMPLATE_DECL'), is_reserved=True, parent=parent_node)
                for child in ast_item.get_children():
                    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                        templ_param = Node(self.tokenizers['RES'].get_token(child.kind.name), is_reserved=True, parent=template_decl)
                        self.create_terminal_nodes(child.spelling, child, templ_param)


            class_decl = Node(self.tokenizers['RES'].get_token('CLASS_DECL'), is_reserved=True, parent=parent_node)
            name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=class_decl)
            self.create_terminal_nodes(ast_item.spelling, ast_item, name)
            cmpnd_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=class_decl)

            return cmpnd_stmt
        elif ast_item.kind == CursorKind.VAR_DECL or ast_item.kind == CursorKind.FIELD_DECL or ast_item.kind == CursorKind.UNEXPOSED_DECL:
            var_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID and ast_item.kind == CursorKind.FIELD_DECL:
                acc_spec = Node(self.tokenizers['RES'].get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=var_decl)
                Node(self.tokenizers['RES'].get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)
                

            self.handle_type(ast_item, var_decl)

            declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
            reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
            self.create_terminal_nodes(ast_item.spelling, ast_item, reference)

            return declarator

        elif utils.is_struct(ast_item):
            # If parent is declarator we are declaring a structure variable so we
            # do not want to declare the enitre structure again
            if self.tokenizers['RES'].get_label(parent_node.token) != 'DECLARATOR':
                class_decl = Node(self.tokenizers['RES'].get_token('STRUCT_DECL'), is_reserved=True, parent=parent_node)
                name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=class_decl)
                self.create_terminal_nodes(ast_item.spelling, ast_item, name)
                cmpnd_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=class_decl)

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
            elif utils.is_operator_token(tokens[-1].spelling):
                op_name = tokens[-1].spelling
                if op_name in ['++', '--']:
                    op_name = 'POST_' + op_name
            else:
                print(f'UNARY OPERATOR EXCEPTION: {[t.spelling for t in tokens]}')
                op_name = ''

            op_name = [op_name]

        else:
            op_name = utils.get_operator(ast_item)
            
        operator = Node(self.tokenizers['RES'].get_token(ast_item.kind.name.strip() + '_' + '_'.join(op_name)), is_reserved=True, parent=parent_node)

        return operator


    def handle_literal(self, ast_item, parent_node, program):
        if self.tokenizers['RES'].get_label(parent_node.token) != 'COMPOUND_STMT':
            lit_type = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            token = next(ast_item.get_tokens(), None)
            if token:                
                Node(self.tokenizers['LITERAL'].get_token(token.spelling), is_reserved=False, parent=lit_type)
            else:
                lit = program[ast_item.extent.start.offset: ast_item.extent.end.offset]
                Node(self.tokenizers['LITERAL'].get_token(lit), is_reserved=False, parent=lit_type)


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

        special_call_expr = ['vector', 'unordered_map', 'pair', 'map', 'queue', 'greater', 'priority_queue', 'bitset', 'multiset', 'set', 'string']

        # if func_name in special_call_expr and len(list(ast_item.get_children())) == 0:
        #     print(func_name, ast_item.spelling, program, ast_item.extent)
        #     return parent_node
        # else:
        if func_name in special_call_expr \
        or (ast_item.referenced and ast_item.referenced.kind == CursorKind.CONSTRUCTOR and len(list(ast_item.get_children())) > 0):

            # Do not call expressions with const before it
            item_type = ast_item.type.spelling.replace('const', '')

            if func_name == 'pair' and len(list(ast_item.get_children())) <= 1:
                return parent_node
            elif func_name == 'pair':
                func_call = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
                ref = Node(self.tokenizers['RES'].get_token('REF_BUILTIN'), is_reserved=True, parent=func_call)
                Node(self.tokenizers['NAME_BUILTIN'].get_token('make_pair'), is_reserved=False, parent=ref) 
            else:
                func_call = Node(self.tokenizers['RES'].get_token('TYPE_CALL_EXPR'), is_reserved=True, parent=parent_node)
                type_kind = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=func_call)

                if func_name == 'set':
                    item_type = f"set<{item_type.split('<')[-1].split(',')[0].replace('>', '').strip()}>"
                self.extract_builtin_type(item_type, type_kind)

            return Node(self.tokenizers['RES'].get_token('ARGUMENTS'), is_reserved=True, parent=func_call)

        else:
            func_call = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.referenced is not None and not "tmp" in str(ast_item.referenced.location):
                ref = Node(self.tokenizers['RES'].get_token('REF_BUILTIN'), is_reserved=True, parent=func_call)
                Node(self.tokenizers['NAME_BUILTIN'].get_token(func_name), is_reserved=False, parent=ref)
            else:
                ref = Node(self.tokenizers['RES'].get_token('REF'), is_reserved=True, parent=func_call)
                Node(self.tokenizers['NAME'].get_token(func_name), is_reserved=False, parent=ref) 

            if len(list(ast_item.get_arguments())) > 0 :
                arg_node =  Node(self.tokenizers['RES'].get_token('ARGUMENTS'), is_reserved=True, parent=func_call)
                
            for arg_item in ast_item.get_arguments():
                parse_item(arg_item, arg_node, program)

        return func_call
        


    def handle_reference(self, ast_item, parent_node):
        if parent_node:
            parent_func_name = ['' if n.children[0].res else self.tokenizers['NAME'].get_label(n.children[0].token)
                                for n in parent_node.children
                                if self.tokenizers['RES'].get_label(n.token) in ['NAME', 'REF', 'REF_BUILTIN'] and self.tokenizers['RES'].get_label(parent_node.token) == 'CALL_EXPR']
        else:
            parent_func_name = []

        if ast_item.spelling \
        and ast_item.spelling not in parent_func_name \
        and not (self.tokenizers['RES'].get_label(parent_node.token) == 'DECLARATOR' and 'REF' in ast_item.kind.name):
            # print('AFTER: ', ast_item.spelling, ast_item.extent)
            if 'tmp' not in str(ast_item.referenced.location):
                reference = Node(self.tokenizers['RES'].get_token('REF_BUILTIN'), True, parent=parent_node)
                Node(self.tokenizers['NAME_BUILTIN'].get_token(ast_item.spelling), False, parent=reference)
            else:
                reference = Node(self.tokenizers['RES'].get_token('REF'), True, parent=parent_node)
                Node(self.tokenizers['NAME'].get_token(ast_item.spelling), False, parent=reference)
            return reference

        elif not ast_item.spelling and ast_item.kind == CursorKind.MEMBER_REF_EXPR:
            tokens = [t.spelling for t in ast_item.get_tokens()]
            member_ref = tokens[tokens.index('.') + 1]
            reference = Node(self.tokenizers['RES'].get_token('REF'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['NAME'].get_token(member_ref), is_reserved=False, parent=reference)
            return reference


    def handle_type_ref(self, ast_item, parent_node):
        type_ref = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        Node(self.tokenizers['NAME'].get_token(ast_item.type.spelling), is_reserved=False, parent=type_ref)

    def handle_for_range(self, ast_item, parent_node):
        stmt = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        # Handle first child that is always a variable declaration
        first_child = next(ast_item.get_children())
        var_decl = Node(self.tokenizers['RES'].get_token(first_child.kind.name), is_reserved=True, parent=stmt)
        self.handle_type(first_child, var_decl)

        declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
        reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
        self.create_terminal_nodes(first_child.spelling, first_child, reference)

        return stmt    


    def handle_cast_expr(self, ast_item, parent_node):
        cast_expr = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        self.handle_type(ast_item, cast_expr)
        return cast_expr

    
    def handle_func_cast_expr(self, ast_item, parent_node):
        func_cast_expr = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        self.handle_type(ast_item, func_cast_expr)
        return func_cast_expr


    def handle_lambda_expr(self, ast_item, parent_node, parse_item, program):
        lambda_expr = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        tokens = [t.spelling for t in ast_item.get_tokens()][1:]
        capture_clause_ended = False
        capture_clause_tokens = []
        for token in tokens:
            if token == ']':
                capture_clause_ended = True

            if capture_clause_ended:
                break

            capture_clause_tokens.append(token)

        capture_clauses = ''.join(capture_clause_tokens).split(',')

        for capture_clause in capture_clauses:
            capt_clause_node = Node(self.tokenizers['RES'].get_token('CAPTURE_CLAUSE'), is_reserved=True, parent=lambda_expr)
            self.create_terminal_nodes(capture_clause, ast_item, capt_clause_node)


        children = ast_item.get_children()
        for child in children:
            parm_declarations = False
            if child.kind == CursorKind.PARM_DECL:
                if not parm_declarations:
                    parm_decl = Node(self.tokenizers['RES'].get_token('PARM_DECL'), is_reserved=True, parent=lambda_expr)
                    parm_declarations = True

                self.handle_type(child, parm_decl)

                declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=parm_decl)
                reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
                self.create_terminal_nodes(child.spelling, child, reference)

                for c in child.get_children():
                    parse_item(c, declarator, program)

        return lambda_expr


    def handle_static_cast_expr(self, ast_item, parent_node):
        static_cast = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        self.handle_type(ast_item, static_cast)

        return static_cast


    def handle_label_stmt(self, ast_item, parent_node):
        stmt = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=parent_node)
        self.create_terminal_nodes(ast_item.spelling, ast_item, name)
        # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=stmt)
        return stmt


    def handle_type(self, ast_item, parent_node, children=None, recursion_level=0):
        canonical_type = ast_item.type.get_canonical()
        node_type = ast_item.type.spelling

        if self.tokenizers['RES'].get_label(parent_node.token) == 'TYPE_DEF':
            node_type = ast_item.underlying_typedef_type.spelling

        elif children is None:
            parent_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=parent_node)

        while canonical_type.kind == TypeKind.POINTER:
            parent_node = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent_node)
            canonical_type = canonical_type.get_pointee()
        

        if utils.is_function(ast_item) or canonical_type.kind == TypeKind.FUNCTIONPROTO: #self.tokenizers['RES'].get_label(parent_node.token) == 'FUNCTION_DECL':
            canonical_type = ast_item.type.get_result()

            node_type = ast_item.type.get_result().spelling

        while canonical_type.kind == TypeKind.POINTER:
            parent_node = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent_node)
            canonical_type = canonical_type.get_pointee()

            node_type = canonical_type.get_pointee()

        if canonical_type.is_const_qualified() or node_type.startswith('const'):
            parent_node = Node(self.tokenizers['RES'].get_token('CONST_QUALIFIED'), is_reserved=True, parent=parent_node)

        for token in ast_item.get_tokens():
            if 'auto' == token.spelling:
                type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)
                Node(self.tokenizers['TYPE'].get_token('auto'), is_reserved=False, parent=type_node)
                return
            break

        if canonical_type.kind in [TypeKind.CONSTANTARRAY, TypeKind.VARIABLEARRAY, TypeKind.INCOMPLETEARRAY, TypeKind.DEPENDENTSIZEDARRAY]:
            parent_node = Node(self.tokenizers['RES'].get_token('TYPE_ARRAY'), is_reserved=True, parent=parent_node)

            array_sizes_node = Node(self.tokenizers['RES'].get_token('ARRAY_SIZES'), is_reserved=True, parent=parent_node)
            for array_size in re.findall('\[.*?\]', ast_item.type.spelling):
                # If it does not only consist of numbers then it is a reference to a variable
                if not all(str(s).isdigit() for s in array_size[1:-1]):
                    # array_size_type = Node(self.tokenizers['RES'].get_token("REF"), is_reserved=True, parent=array_sizes_node)
                    self.extract_variable_array_sizes_subtree(array_size[1:-1], array_sizes_node)
                    # Node(self.tokenizers['NAME'].get_token(array_size[1:-1]), is_reserved=False, parent=array_size_type)
                else:
                    array_size_type = Node(self.tokenizers['RES'].get_token("INTEGER_LITERAL"), is_reserved=True, parent=array_sizes_node)
                    Node(self.tokenizers['LITERAL'].get_token(array_size[1:-1]), is_reserved=False, parent=array_size_type)

            node_type = re.sub('\[.*?\]', '', node_type)

        # For example: int& a = x (left value reference) or int&& b = 30 (right value reference)
        elif canonical_type.kind == TypeKind.LVALUEREFERENCE or canonical_type.kind == TypeKind.RVALUEREFERENCE:
            parent_node = Node(self.tokenizers['RES'].get_token(ast_item.type.kind.name), is_reserved=True, parent=parent_node)

        self.extract_builtin_type(node_type, parent_node)


    def extract_variable_array_sizes_subtree(self, code, parent_node):
        tu = self.cindex.parse('tmp_array.cpp', args=['-std=c++20'], unsaved_files=[('tmp_array.cpp', code)])
        tokens = list(tu.get_tokens(extent=tu.cursor.extent))
        operators = [(t.spelling, idx) for idx, t in enumerate(tokens) if t.kind == TokenKind.PUNCTUATION]

        self.create_subtree(tokens, operators, parent_node)


    def create_subtree(self, tokens, operators, parent_node):
        for op, idx in operators:
            if idx + 1 < len(tokens) - 1:
                op_node = Node(self.tokenizers['RES'].get_token(f'BINARY_OPERATOR_{op}'), is_reserved=True, parent=parent_node)
                t = tokens[idx - 1]
                if t.kind == TokenKind.IDENTIFIER:
                    ref = Node(self.tokenizers['RES'].get_token('REF'), is_reserved=True, parent=op_node)
                    Node(self.tokenizers['NAME'].get_token(t.spelling), is_reserved=False, parent=ref)
                else:
                    lit = Node(self.tokenizers['RES'].get_token('INTEGER_LITERAL'), is_reserved=True, parent=op_node)
                    Node(self.tokenizers['LITERAL'].get_token(t.spelling), is_reserved=False, parent=lit)

                operators.remove((op, idx))
                self.create_subtree(tokens, operators, op_node)
            else:
                op_node = Node(self.tokenizers['RES'].get_token(f'BINARY_OPERATOR_{op}'), is_reserved=True, parent=parent_node)
                
                for t in [tokens[idx - 1], tokens[idx + 1]]:
                    if t.kind == TokenKind.IDENTIFIER:
                        ref = Node(self.tokenizers['RES'].get_token('REF'), is_reserved=True, parent=op_node)
                        Node(self.tokenizers['NAME'].get_token(t.spelling), is_reserved=False, parent=ref)
                    else:
                        lit = Node(self.tokenizers['RES'].get_token('INTEGER_LITERAL'), is_reserved=True, parent=op_node)
                        Node(self.tokenizers['LITERAL'].get_token(t.spelling), is_reserved=False, parent=lit)

        if len(tokens) == 1:
            t = tokens[0]
            if t.kind == TokenKind.IDENTIFIER:
                ref = Node(self.tokenizers['RES'].get_token('REF'), is_reserved=True, parent=parent_node)
                Node(self.tokenizers['NAME'].get_token(t.spelling), is_reserved=False, parent=ref)
            else:
                lit = Node(self.tokenizers['RES'].get_token('INTEGER_LITERAL'), is_reserved=True, parent=parent_node)
                Node(self.tokenizers['LITERAL'].get_token(t.spelling), is_reserved=False, parent=lit)


    def extract_builtin_type(self, type_string, parent_node):
        for _ in range(len(re.findall('\*', type_string))):
            parent_node = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent_node)

        type_string = type_string.replace('*', '')\
                                 .replace('&', '')\
                                 .replace('const', '')\
                                 .replace('std::', '')\
                                 .replace('::value_type', '')\
                                 .replace('*', '')\
                                 .replace('&', '')\
                                 .replace('struct', '').strip()

        # Remove spaces between non-alphanumeric characters and commas
        type_string = re.sub('\s*([^A-Za-z,])\s*', r'\1', type_string)


        self.build_type_subtree(type_string, parent_node)


    def build_type_subtree(self, type_string, parent_node):
        # Regex that selects the inner <....> of a type (the inner part might contain <..> too)
        inner_brackets_regex = '<.*>'

        # Remove the inner part to get the outer type e.g. vector<int> -> vector
        outer_type = re.sub(inner_brackets_regex, '', type_string)
        # print(outer_type, type_string)
        
        # If outer type is not empty
        if len(outer_type) > 0:  
            # Obtain only the inner part vector<int> -> int
            type_strings = re.sub(outer_type, '', type_string, 1)[1:-1]
            
            # if there is no inner part, then we build type nodes (it is not a record type)
            if len(type_strings) == 0:
                for t in outer_type.split(','):
                    self.build_type_node(t.strip(), False, parent_node)
                    
            # If there is an innner part, we build a type record node
            else:
                parent_node = self.build_type_node(outer_type, True, parent_node)        


            # Split the inner part: vector<int>, vector<long long> into two seperate children
            type_strings = type_strings.split('>,')

            # Recursively process the inner parts
            for idx, type_string in enumerate(type_strings):
                if len(type_strings) > 1 and idx < len(type_strings) - 1:
                    type_string += '>'
                self.build_type_subtree(type_string.strip(), parent_node)


    def build_type_node(self, type_string, record_type, parent_node):
        if record_type:
            type_record = Node(self.tokenizers['RES'].get_token('TYPE_RECORD'), is_reserved=True, parent=parent_node)
            self.create_type_node(type_string, type_record)
            
            return Node(self.tokenizers['RES'].get_token('TYPE_RECORD_ELEMENTS'), is_reserved=True, parent=type_record)
        
        else:
            self.create_type_node(type_string, parent_node)


    def create_type_node(self, type_string, parent_node):
        if type_string.isdigit():
            type_node = Node(self.tokenizers['RES'].get_token('INTEGER_LITERAL'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['LITERAL'].get_token(type_string), is_reserved=False, parent=type_node)

        elif type_string in self.builtin_types:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['TYPE'].get_token(type_string), is_reserved=False, parent=record_type)

        elif 'type-parameter' in type_string:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['TYPE'].get_token('T'), is_reserved=False, parent=record_type)
            
        else:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['NAME'].get_token(type_string), is_reserved=False, parent=record_type)
            


    # Create terminal nodes with the possibility to split the terminal labels by clang defined tokens
    # e.g. "long long int" -> ["long", "long", "int"]
    # To greatly reduce the numbe of unique terminal tokens if the dataset is large
    def create_terminal_nodes(self, label, ast_item, parent_node, tokens=None):
        if self.split_terminals:
            # Splilt label by: '[', ']', '<', '>', ' ', '::', ','
            split_label = [el for el in re.split('(\[|\]|<|>| |::|,)', label) if len(el.strip()) > 0]

            for label in split_label:
                Node(self.tokenizers['NAME'].get_token(label), is_reserved=False, parent=parent_node)
        else:
            Node(self.tokenizers['NAME'].get_token(label), is_reserved=False, parent=parent_node)