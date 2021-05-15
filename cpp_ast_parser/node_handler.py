import utils
from clang.cindex import CursorKind, AccessSpecifier, TypeKind
from tree_node import Node
import re

class NodeHandler:
    def __init__(self, tokenizers, split_terminals):
        # Set reserved label and non reserved label tokenizers
        self.tokenizers = tokenizers
        self.split_terminals = split_terminals

        self.builtin_types = ['int', 'long', 'long long', 'double', 'long double', 'unsigned long long', 'vector',
                            'void', 'map', 'auto', 'short', 'deque', 'bool', 'pair', 'int32_t', 'queue', 'priority_queue',
                            'istream_iterator', 'complex', 'char', 'set', 'unsigned int', 'string', 'stack', 'unordered_map',
                            'tuple', 'multiset', 'unsigned long', 'unsigned char', 'signed char', 'signed int', 'short int',
                            'unsigned short int', 'signed short int', 'long int', 'signed long int', 'unsigned long int', 'long long int',
                            'unsigned long long int', 'float', 'wchar_t', 'bitset', 'unordered_set', 'basic_string', 'array', 'forward_list',
                            'shared_ptr', 'std::__cxx11::basic_string<char>', 'std::basic_string<char>', 'std::string', 'vector<int>', 
                            'vector<long long>', 'queue<int>', 'std::pair<int, int>', 'std::vector<int, std::allocator<int>>', 'pair<int, int>',
                            'std::vector<std::pair<int, int>, std::allocator<std::pair<int, int>>>::value_type', 'std::pair<long long, long long>',
                            'std::vector<long long, std::allocator<long long>>', 'vector<bool>', 'stack<int>', 'vector<vector<int>>',
                            'std::vector<std::pair<long long, long long>, std::allocator<std::pair<long long, long long>>>::value_type',
                            'std::basic_stringstream<char>', 'int64_t', 'vector<std::string>', 'pair<long long, long long>', 'vector<pair<int, int>>',
                            'greater<int>'
                            ]

    def handle_typedef(self, ast_item, parent_node):
        # Set top node as TYPEDEF_DECL
        typedef_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        # Set first child als TYPE_DEF
        type_def = Node(self.tokenizers['RES'].get_token('TYPE_DEF'),is_reserved=True, parent=typedef_decl)
        
        # Set value of TYPE def to type of TYPEDEF
        # print(ast_item.type.get_canonical().kind, ast_item.type.spelling, ast_item.type.get_canonical().spelling, ast_item.underlying_typedef_type.spelling, [(c.spelling, c.kind, c.type.spelling) for c in ast_item.get_children()])
    
        
        self.handle_type(ast_item, type_def)
        # self.create_terminal_nodes(ast_item.underlying_typedef_type.spelling, ast_item, type_def)
        # Node(self.tn.get_token(ast_item.underlying_typedef_type.spelling), is_reserved=False, parent=type_def)

        # Set second child as IDENTIFIER
        identifier = Node(self.tokenizers['RES'].get_token('IDENTIFIER'), is_reserved=True, parent=typedef_decl)
        # Set value of IDENTIFIER to spelling of node
        self.create_terminal_nodes(ast_item.spelling, ast_item, identifier)
        # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=identifier)


    def handle_declaration(self, ast_item, parent_node, parse_item, program): 
        if utils.is_function(ast_item):
            if (ast_item.kind == CursorKind.FUNCTION_TEMPLATE):
                template_decl = Node(self.tokenizers['RES'].get_token('TEMPLATE_DECL'), is_reserved=True, parent=parent_node)
                for child in ast_item.get_children():
                    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                        templ_param = Node(self.tokenizers['RES'].get_token(child.kind.name), is_reserved=True, parent=template_decl)
                        self.create_terminal_nodes(child.spelling, child, templ_param)
                        # Node(self.tn.get_token(child.spelling), is_reserved=False, parent=templ_param)

            
            func_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID:
                acc_spec = Node(self.tokenizers['RES'].get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=func_decl)
                Node(self.tokenizers['RES'].get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)


            name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=func_decl)
            self.create_terminal_nodes(ast_item.spelling, ast_item, name)
            # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
            if ast_item.kind != CursorKind.CONSTRUCTOR:
                # return_type = Node(self.tokenizers['RES'].get_token('RETURN_TYPE'), is_reserved=True, parent=func_decl)
                self.handle_type(ast_item, func_decl)
                # print(ast_item.type.get_result())
                # self.create_terminal_nodes(ast_item.type.get_result().spelling, ast_item, return_type)
                # Node(self.tn.get_token(ast_item.type.get_result().spelling), is_reserved=False, parent=return_type)

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
                    # type_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=parm_decl)

                    # Node(self.tn.get_token(child.type.spelling), is_reserved=False, parent=type_node)
                    # self.create_terminal_nodes(child.type.spelling, child, type_node)

                    declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=parm_decl)
                    reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
                    self.create_terminal_nodes(child.spelling, child, reference)
                    # Node(self.tn.get_token(child.spelling), is_reserved=False, parent=reference)

                    for c in child.get_children():
                        parse_item(c, declarator, program)

            # Get children of constructor which are not parameters or compount statements, thus are constructor initializers
            if ast_item.kind == CursorKind.CONSTRUCTOR:
                constructor_inits = [child for child in ast_item.get_children() if child.kind != CursorKind.COMPOUND_STMT and child.kind != CursorKind.PARM_DECL]
                for i in range(0,len(constructor_inits), 2):
                    constr_init = Node(self.tokenizers['RES'].get_token('CONSTRUCTOR_INITIALIZER'), is_reserved=True, parent=func_decl)

                    member_ref = Node(self.tokenizers['RES'].get_token(constructor_inits[i].kind.name), is_reserved=True, parent=constr_init)
                    self.create_terminal_nodes(constructor_inits[i].spelling, constructor_inits[i], member_ref)
                    # Node(self.tn.get_token(constructor_inits[i].spelling), is_reserved=False, parent=member_ref)

                    parse_item(constructor_inits[i + 1], constr_init, program)                

            return func_decl

        elif utils.is_class(ast_item):
            if ast_item.kind == CursorKind.CLASS_TEMPLATE:
                template_decl = Node(self.tokenizers['RES'].get_token('TEMPLATE_DECL'), is_reserved=True, parent=parent_node)
                for child in ast_item.get_children():
                    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                        templ_param = Node(self.tokenizers['RES'].get_token(child.kind.name), is_reserved=True, parent=template_decl)
                        self.create_terminal_nodes(child.spelling, child, templ_param)
                        # Node(self.tn.get_token(child.spelling), is_reserved=False, parent=templ_param)


            class_decl = Node(self.tokenizers['RES'].get_token('CLASS_DECL'), is_reserved=True, parent=parent_node)
            name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=class_decl)
            self.create_terminal_nodes(ast_item.spelling, ast_item, name)
            # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
            cmpnd_stmt = Node(self.tokenizers['RES'].get_token('COMPOUND_STMT'), is_reserved=True, parent=class_decl)

            return cmpnd_stmt
        elif ast_item.kind == CursorKind.VAR_DECL or ast_item.kind == CursorKind.FIELD_DECL or ast_item.kind == CursorKind.UNEXPOSED_DECL:
            var_decl = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

            if ast_item.access_specifier != AccessSpecifier.INVALID and ast_item.kind == CursorKind.FIELD_DECL:
                acc_spec = Node(self.tokenizers['RES'].get_token('ACCESS_SPECIFIER'), is_reserved=True, parent=var_decl)
                Node(self.tokenizers['RES'].get_token(ast_item.access_specifier.name), is_reserved=True, parent=acc_spec)

            self.handle_type(ast_item, var_decl)
            # type_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=var_decl)
            # unexposed declarations and lambda declarations get type auto
            # if ast_item.kind == CursorKind.UNEXPOSED_DECL or 'lambda' in ast_item.type.spelling:
            #     Node(self.tn.get_token('auto'), is_reserved=False, parent=type_node)
            # else:
            #     self.create_terminal_nodes(ast_item.type.spelling, ast_item, type_node)
                # Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=type_node)
            declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
            reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
            self.create_terminal_nodes(ast_item.spelling, ast_item, reference)
            # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=reference)

            return declarator

        elif utils.is_struct(ast_item):
            # If parent is declarator we are declaring a structure variable so we
            # do not want to declare the enitre structure again
            if self.tokenizers['RES'].get_label(parent_node.token) != 'DECLARATOR':
                class_decl = Node(self.tokenizers['RES'].get_token('STRUCT_DECL'), is_reserved=True, parent=parent_node)
                name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=class_decl)
                self.create_terminal_nodes(ast_item.spelling, ast_item, name)
                # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=name)
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

        # print(ast_item.kind.name.strip() + '_' + '_'.join(op_name))
            
        operator = Node(self.tokenizers['RES'].get_token(ast_item.kind.name.strip() + '_' + '_'.join(op_name)), is_reserved=True, parent=parent_node)

        return operator


    def handle_literal(self, ast_item, parent_node, program):
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

        special_call_expr = ['vector', 'unordered_map', 'set', 'pair', 'map', 'queue', 'greater', 'priority_queue', 'bitset']

        if func_name in special_call_expr and len(list(ast_item.get_children())) == 0:
            return parent_node
        else:
            func_call = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
            ref = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=func_call)

            if len(list(ast_item.get_arguments())) > 0 :
                arg_node =  Node(self.tokenizers['RES'].get_token('ARGUMENTS'), is_reserved=True, parent=func_call)
                
            for arg_item in ast_item.get_arguments():
                parse_item(arg_item, arg_node, program)

            if func_name in special_call_expr \
            or (ast_item.referenced and ast_item.referenced.kind == CursorKind.CONSTRUCTOR and len(list(ast_item.get_children())) > 0):
                # Do not call expressions with const before it
                item_type = ast_item.type.spelling.replace('const', '')

                # In special call expr the declaration tokens clang provides will not be correct
                # so we manually get them
                # Node(self.tn.get_token(func_name), is_reserved=False, parent=ref)
                
                # tokens = [self.tn.get_label(t.token) for t in parent_node.parent.children]
                # self.create_terminal_nodes(item_type, ast_item, ref, tokens)
                Node(self.tokenizers['NAME'].get_token(item_type), is_reserved=False, parent=ref)
                return Node(self.tokenizers['RES'].get_token('ARGUMENTS'), is_reserved=True, parent=func_call)
            else:
                Node(self.tokenizers['NAME'].get_token(func_name), is_reserved=False, parent=ref)

            # if '::' in [t.spelling for t in ast_item.get_tokens()]:

            #     # Check if there is a already a type ref child
            #     type_ref_child = False
            #     for child in ast_item.walk_preorder():
            #         if child.kind == CursorKind.TYPE_REF:
            #             type_ref_child = True
            #             break

            #     # if there is no child of kind type_ref, then we have to add it manually
            #     if not type_ref_child:
            #         type_ref = ''
            #         for token in ast_item.get_tokens():
            #             if token.spelling == '::':
            #                 break
            #             else:
            #                 type_ref += token.spelling


            #         type_ref_node = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=func_call)
            #         print([t.spelling for t in ast_item.get_tokens()], type_ref)
            #         self.create_terminal_nodes(type_ref, ast_item, type_ref_node)
            #         # Node(self.tn.get_token(type_ref), is_reserved=False, parent=type_ref_node)


            return func_call
            


    def handle_reference(self, ast_item, parent_node):
        if parent_node:
            parent_func_name = ['' if n.children[0].res else self.tokenizers['NAME'].get_label(n.children[0].token)
                                for n in parent_node.children
                                if self.tokenizers['RES'].get_label(n.token) == 'NAME' and self.tokenizers['RES'].get_label(parent_node.token) != 'DECLARATOR']
        else:
            parent_func_name = []

        if ast_item.spelling \
        and ast_item.spelling not in parent_func_name:

            reference = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), True, parent=parent_node)
            Node(self.tokenizers['NAME'].get_token(ast_item.spelling), False, parent=reference)

            return reference


    def handle_type_ref(self, ast_item, parent_node):
        type_ref = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        # self.create_terminal_nodes(ast_item.type.spelling, ast_item, type_ref)
        Node(self.tokenizers['NAME'].get_token(ast_item.type.spelling), is_reserved=False, parent=type_ref)

    def handle_for_range(self, ast_item, parent_node):
        stmt = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)

        # Handle first child that is always a variable declaration
        first_child = next(ast_item.get_children())
        var_decl = Node(self.tokenizers['RES'].get_token(first_child.kind.name), is_reserved=True, parent=stmt)
        self.handle_type(first_child, var_decl)
        # type_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=var_decl)
        # self.create_terminal_nodes(first_child.type.spelling, first_child, type_node)
        # Node(self.tn.get_token(first_child.type.spelling), is_reserved=False, parent=type_node)
        declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=var_decl)
        reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
        self.create_terminal_nodes(first_child.spelling, first_child, reference)
        # Node(self.tn.get_token(first_child.spelling), is_reserved=False, parent=reference)

        return stmt    


    def handle_cast_expr(self, ast_item, parent_node):
        cast_expr = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        # print([(c.kind, c.spelling, c.type.spelling)  for c in ast_item.get_children()])
        # if not CursorKind.TYPE_REF in [c.kind for c in ast_item.get_children()]:
        self.handle_type(ast_item, cast_expr)
            # cast_type = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=cast_expr)
            # self.create_terminal_nodes(ast_item.type.spelling, ast_item, cast_type)
            # Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=cast_type)
        return cast_expr

    
    def handle_func_cast_expr(self, ast_item, parent_node):
        func_cast_expr = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        self.handle_type(ast_item, func_cast_expr)
        # cast_type = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=func_cast_expr)
        # self.create_terminal_nodes(ast_item.type.spelling, ast_item, cast_type)
        # Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=cast_type)
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
            # Node(self.tn.get_token(capture_clause), is_reserved=False, parent=capt_clause_node)


        children = ast_item.get_children()
        for child in children:
            parm_declarations = False
            if child.kind == CursorKind.PARM_DECL:
                if not parm_declarations:
                    parm_decl = Node(self.tokenizers['RES'].get_token('PARM_DECL'), is_reserved=True, parent=lambda_expr)
                    parm_declarations = True

                self.handle_type(child, parm_decl)
                # type_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=parm_decl)

                # # If parameter type cannot be resolved, it is auto
                # if 'type-parameter' in child.type.spelling:
                #     Node(self.tn.get_token('auto'), is_reserved=False, parent=type_node)
                # else:
                #     self.create_terminal_nodes(child.type.spelling, child, type_node)
                    # Node(self.tn.get_token(child.type.spelling), is_reserved=False, parent=type_node)

                declarator = Node(self.tokenizers['RES'].get_token('DECLARATOR'), is_reserved=True, parent=parm_decl)
                reference = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=declarator)
                self.create_terminal_nodes(child.spelling, child, reference)
                # Node(self.tn.get_token(child.spelling), is_reserved=False, parent=reference)

                for c in child.get_children():
                    parse_item(c, declarator, program)

        return lambda_expr


    def handle_static_cast_expr(self, ast_item, parent_node):
        static_cast = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        self.handle_type(ast_item, static_cast)
        # cast_type = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=static_cast)
        # self.create_terminal_nodes(ast_item.type.spelling, ast_item, cast_type)
        # Node(self.tn.get_token(ast_item.type.spelling), is_reserved=False, parent=cast_type)

        return static_cast


    def handle_label_stmt(self, ast_item, parent_node):
        stmt = Node(self.tokenizers['RES'].get_token(ast_item.kind.name), is_reserved=True, parent=parent_node)
        name = Node(self.tokenizers['RES'].get_token('NAME'), is_reserved=True, parent=parent_node)
        self.create_terminal_nodes(ast_item.spelling, ast_item, name)
        # Node(self.tn.get_token(ast_item.spelling), is_reserved=False, parent=stmt)
        return stmt


    def handle_type(self, ast_item, parent_node, children=None, recursion_level=0):
        canonical_type = ast_item.type.get_canonical()
        function_type =False

        if children is None:
            parent_node = Node(self.tokenizers['RES'].get_token('TYPE_KIND'), is_reserved=True, parent=parent_node)

        while canonical_type.kind == TypeKind.POINTER:
            parent_node = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent_node)
            canonical_type = canonical_type.get_pointee()
        

        if utils.is_function(ast_item) or canonical_type.kind == TypeKind.FUNCTIONPROTO: #self.tokenizers['RES'].get_label(parent_node.token) == 'FUNCTION_DECL':
            canonical_type = ast_item.type.get_result()
            function_type = True

        while canonical_type.kind == TypeKind.POINTER:
            parent_node = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent_node)
            canonical_type = canonical_type.get_pointee()

        if canonical_type.is_const_qualified():
            parent_node = Node(self.tokenizers['RES'].get_token('CONST_QUALIFIED'), is_reserved=True, parent=parent_node)

        for token in ast_item.get_tokens():
            if 'auto' == token.spelling:
                type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)
                Node(self.tokenizers['TYPE'].get_token('auto'), is_reserved=False, parent=type_node)
                return
            break


        # E.g. vector<int> or pair<long long, pair<long long, long long>> or std::string
        if canonical_type.kind in [TypeKind.RECORD, TypeKind.ELABORATED] or children is not None:
            record = Node(self.tokenizers['RES'].get_token('TYPE_RECORD'), is_reserved=True, parent=parent_node)

            if children is None:
                children = list(ast_item.get_children())

            if children[0].kind == CursorKind.TYPE_REF:
                record_type = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=record)
                Node(self.tokenizers['NAME'].get_token(children[0].type.get_canonical().spelling), is_reserved=False, parent=record_type)
            elif len(children[0].spelling) > 0: # children[0].kind == CursorKind.TEMPLATE_REF:
                if children[0].kind == CursorKind.TEMPLATE_REF:
                    self.extract_builtin_type(children[0].spelling, record)
                    # record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=record)
                    # if children[0].spelling not in self.builtin_types:
                    #     print(children[0].spelling)
                    # Node(self.tokenizers['TYPE'].get_token(children[0].spelling), is_reserved=False, parent=record_type)
                else:
                    record_type = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=record)
                    Node(self.tokenizers['NAME'].get_token(children[0].spelling), is_reserved=False, parent=record_type)
            else:
                
                record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=record)
                Node(self.tokenizers['TYPE'].get_token('auto'), is_reserved=False, parent=record_type)
                return

            # print(canonical_type.spelling, ast_item.spelling, canonical_type.kind, [(c.spelling, c.kind.name, c.type.spelling) for c in children])

                
            # Type refs that are already handled, we need to find the types not specified as children
            # For example, in pair<int, ll> where ll is a type ref pointing to long long, the ll will be
            # handled, but we still need to handle int ourselves as it will not be in the children
            type_refs = []
            records = []

            for index, child in enumerate(children[1:]):
                if child.kind == CursorKind.TYPE_REF:
                    type_refs.append(child)
                    # Node(child.type.get_canonical().spelling, is_reserved=False, parent=record_elements)
                elif child.kind == CursorKind.TEMPLATE_REF:
                    records.append((child, index + 1))

            if self.tokenizers['RES'].get_label(parent_node.parent.token) == 'TYPE_DEF':
                spelling = ast_item.underlying_typedef_type.spelling
            else:
                spelling = ast_item.type.spelling

            if '<' in spelling:
                record_elements = Node(self.tokenizers['RES'].get_token('TYPE_RECORD_ELEMENTS'), is_reserved=True, parent=record)
                # get types to handle on recursion level, for example: pair<int, pair<ll, int>> and recursion level 0
                # Then we want to consider [int, pair] and on recursion level 1 we want to consider [ll, int]
                # print(ast_item.type.spelling, )

                record_items = re.split('<', spelling)
                types = [el.strip() for el in record_items[min(recursion_level + 1, len(record_items) - 1)].split('>')[0].split(',')]

                for typ in types:
                    type_ref_match = next((item for item in type_refs if item.type.spelling == typ), None)
                    record_match = next((item for item in records if item[0].spelling == typ), None)
                    if type_ref_match is not None:
                        # if type_ref_match.type.kind == TypeKind.TYPEDEF:
                            # print(type_ref_match.type.get_canonical().spelling)
                        #     type_ref = Node('TYPE', is_reserved=True, parent=record_elements)
                            
                        # else:
                        type_ref = Node('TYPE_REF', is_reserved=True, parent=record_elements)
                            # print(type_ref_match.type.get_canonical().spelling, type_ref_match.type.spelling)

                        Node(self.tokenizers['NAME'].get_token(type_ref_match.type.spelling), is_reserved=False, parent=type_ref)
                    elif record_match is not None:
                        self.handle_type(ast_item, record_elements, children[record_match[1]:], recursion_level + 1)
                    else:
                        self.extract_builtin_type(typ, record_elements)
                        


        elif canonical_type.kind in [TypeKind.CONSTANTARRAY, TypeKind.VARIABLEARRAY, TypeKind.INCOMPLETEARRAY, TypeKind.DEPENDENTSIZEDARRAY]:
            array = Node(self.tokenizers['RES'].get_token('TYPE_ARRAY'), is_reserved=True, parent=parent_node)

            if canonical_type.get_array_element_type().kind == TypeKind.RECORD:
                self.handle_type(ast_item, array, list(ast_item.get_children()), recursion_level)
            elif canonical_type.get_array_element_type().kind == TypeKind.CONSTANTARRAY:
                array_type = canonical_type.get_array_element_type()

                while(array_type.kind == TypeKind.CONSTANTARRAY):
                    array_type = array_type.get_array_element_type()


                if array_type.kind == TypeKind.RECORD:
                    self.handle_type(ast_item, array, list(ast_item.get_children()), recursion_level)
                else:
                    self.extract_builtin_type(array_type.spelling, array)
                    # type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=array)
                    # print(array_type.spelling)
                    # Node(self.tokenizers['TYPE'].get_token(array_type.spelling), is_reserved=False, parent=type_node)

            else:
                self.extract_builtin_type(canonical_type.get_array_element_type().spelling, parent=array)
                # print(canonical_type.get_array_element_type().spelling)
                # type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=array)
                # Node(self.tokenizers['TYPE'].get_token(canonical_type.get_array_element_type().spelling), is_reserved=False, parent=type_node)


            array_sizes_node = Node(self.tokenizers['RES'].get_token('ARRAY_SIZES'), is_reserved=True, parent=array)
            for array_size in re.findall('\[.*?\]', ast_item.type.spelling):
                # If it does not only consist of numbers then it is a reference to a variable
                if not all(str(s).isdigit() for s in array_size[1:-1]):
                    array_size_type = Node(self.tokenizers['RES'].get_token("DECL_REF_EXPR"), is_reserved=True, parent=array_sizes_node)
                    Node(self.tokenizers['NAME'].get_token(array_size[1:-1]), is_reserved=False, parent=array_size_type)
                else:
                    array_size_type = Node(self.tokenizers['RES'].get_token("INTEGER_LITERAL"), is_reserved=True, parent=array_sizes_node)
                    Node(self.tokenizers['LITERAL'].get_token(array_size[1:-1]), is_reserved=False, parent=array_size_type)


        # For example: int& a = x (left value reference) or int&& b = 30 (right value reference)
        elif canonical_type.kind == TypeKind.LVALUEREFERENCE or canonical_type.kind == TypeKind.RVALUEREFERENCE:
            value_ref = Node(self.tokenizers['RES'].get_token(ast_item.type.kind.name), is_reserved=True, parent=parent_node)

            children = list(ast_item.get_children())
            has_type = False

            for child in ast_item.get_children():
                if child.kind == CursorKind.TEMPLATE_REF:
                    has_type = True
                    self.handle_type(ast_item, value_ref, children, recursion_level)
                    break
                elif child.kind == CursorKind.TYPE_REF:
                    has_type = True
                    type_ref = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=value_ref)
                    Node(self.tokenizers['NAME'].get_token(child.type.spelling), is_reserved=False, parent=type_ref)


            if not has_type:
                self.extract_builtin_type(ast_item.type.get_canonical().spelling, value_ref)
                


        # For example: type parameters const As&... have canonical type spelling type-parameter-0-0
        elif canonical_type.kind in [TypeKind.UNEXPOSED, TypeKind.TYPEDEF, TypeKind.ENUM]:
            # print(ast_item.type.spelling)
            type_node = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=parent_node)
            if function_type or canonical_type.kind == TypeKind.TYPEDEF:
                Node(self.tokenizers['NAME'].get_token(canonical_type.spelling.replace('const', '').strip()), is_reserved=False, parent=type_node)    
            else:
                Node(self.tokenizers['NAME'].get_token(ast_item.type.spelling.replace('const', '').strip()), is_reserved=False, parent=type_node)

        elif canonical_type.kind != TypeKind.INVALID:
            type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)

            # if type_def:
            # print(ast_item.type.spelling, canonical_type.spelling, ast_item.kind, ast_item.spelling, [t.spelling for t in ast_item.get_tokens()])

            if canonical_type.spelling.replace('const', '').strip() not in self.builtin_types:
                # print(canonical_type.get_result().spelling, [t.spelling for t in ast_item.get_tokens()])
                print(canonical_type.spelling.replace('const', '').strip(), canonical_type.kind, [t.spelling for t in ast_item.get_tokens()])
            # print(canonical_type.spelling.replace('const', '').strip(), parent_node)
            Node(self.tokenizers['TYPE'].get_token(canonical_type.spelling.replace('const', '').strip()), is_reserved=False, parent=type_node)

        else:
            type_node = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent_node)
            Node(self.tokenizers['TYPE'].get_token('auto'), is_reserved=False, parent=type_node)
                    
                    
                # print(ast_item.type.spelling, [(c.spelling, c.type.spelling, c.kind.name) for c in ast_item.get_children()])
                # print(ast_item.spelling, canonical_type.get_array_element_type().get_array_element_type().kind.name, canonical_type.get_array_element_type().spelling)
            # print(ast_item.type.spelling, canonical_type.get_array_element_type().kind.name, ast_item.type.get_array_size())
            # print(ast_item.type.spelling, [(c.spelling, c.type.spelling, c.kind.name) for c in ast_item.get_children()])

            

            




            # print(ast_item.type.spelling, [(c.spelling, c.type.spelling, c.type.get_canonical().spelling, c.kind.name) for c in ast_item.get_children()])
            # print(ast_item.type.spelling, [(c.spelling, c.type.get_canonical().spelling, c.kind.name) for c in ast_item.walk_preorder()])
            # print(ast_item.type.spelling, [(c.spelling, c.type.spelling, c.type.get_canonical().spelling, c.kind.name) for c in self.get_type_children(ast_item)])
            # print(ast_item.spelling, [(c.spelling, c.type.spelling, c.kind.name) for c in ast_item.get_children()])



        # VAR DECL:
        # if ast_item.kind == CursorKind.UNEXPOSED_DECL or 'lambda' in ast_item.type.spelling:
        #     Node(self.tn.get_token('auto'), is_reserved=False, parent=type_node)
        # else:
        #     self.create_terminal_nodes(ast_item.type.spelling, ast_item, type_node)


        # LAMBDA EXPR:
        # If parameter type cannot be resolved, it is auto
        # if 'type-parameter' in ast_item.type.spelling:
        #     Node(self.tn.get_token('auto'), is_reserved=False, parent=type_node)
        # else:
        #     self.create_terminal_nodes(ast_item.type.spelling, ast_item, type_node)



        # print(ast_item.spelling, [(c.spelling, c.type.spelling, c.kind.name) for c in ast_item.get_children()])

    def extract_builtin_type(self, typ, parent):
        for _ in range(len(re.findall('\*', typ))):
            parent = Node(self.tokenizers['RES'].get_token('POINTER'), is_reserved=True, parent=parent)

        typ = typ.replace('*', '').replace('&', '').replace('const', '').strip()

        if typ.isdigit():
            type_node = Node(self.tokenizers['RES'].get_token('INTEGER_LITERAL'), is_reserved=True, parent=parent)
            Node(self.tokenizers['LITERAL'].get_token(typ), is_reserved=False, parent=type_node)

        elif typ in self.builtin_types:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent)
            Node(self.tokenizers['TYPE'].get_token(typ), is_reserved=False, parent=record_type)

        elif 'type-parameter' in typ:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE'), is_reserved=True, parent=parent)
            Node(self.tokenizers['TYPE'].get_token('T'), is_reserved=False, parent=record_type)
            
        else:
            record_type = Node(self.tokenizers['RES'].get_token('TYPE_REF'), is_reserved=True, parent=parent)
            Node(self.tokenizers['NAME'].get_token(typ), is_reserved=False, parent=record_type)
            


    # Create terminal nodes with the possibility to split the terminal labels by clang defined tokens
    # e.g. "long long int" -> ["long", "long", "int"]
    # To greatly reduce the numbe of unique terminal tokens if the dataset is large
    def create_terminal_nodes(self, label, ast_item, parent_node, tokens=None):
        if self.split_terminals:
            # Splilt label by: '[', ']', '<', '>', ' ', '::', ','
            split_label = [el for el in re.split('(\[|\]|<|>| |::|,)', label) if len(el.strip()) > 0]
            # split_label = []
            # for t in tokens if tokens is not None else [tok.spelling for tok in ast_item.get_tokens()]:
            #     if t in label:
            #         # Might be tokens not in the token list we would still like to add
            #         # Example: say we have code int[maxN] where maxN = 1, we get type int[1],
            #         # but 1 is not in tokens, instead maxN is, we still like to add the 1.
            #         if not label.strip().startswith(t):
            #             pre_token = label.split(t)[0].strip()
            #             label = label.replace(pre_token, '', 1)
            #             split_label.append(pre_token)
            #         label = label.replace(t, '', 1)
            #         split_label.append(t)
                
            #     if len(label.strip()) == 0:
            #         break

            # # Add any leftover label -> int n,m for VAR DECL of m the type will be int,
            # #  but the tokens will not contain this int, we would still like to add it.
            # if len(label.strip()) > 0:
            #     split_label.append(label.strip())

            # print(split_label, tokens)

            for label in split_label:
                Node(self.tokenizers['NAME'].get_token(label), is_reserved=False, parent=parent_node)
        else:
            Node(self.tokenizers['NAME'].get_token(label), is_reserved=False, parent=parent_node)

        # return '|'.join([str(self.tn.get_token(lab)) for lab in split_label])
