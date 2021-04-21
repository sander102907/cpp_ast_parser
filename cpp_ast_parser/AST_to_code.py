from anytree.importer import JsonImporter
from anytree import RenderTree
from anytree.search import find
from utils import assignment_operators, add_includes_usings
import threading
import multiprocessing
import queue as queue
import os
from tqdm import tqdm
import json
import re
import pandas as pd
from tokenizer import Tokenizer
import gzip

class AstToCodeParser:
    def __init__(self, input_folder, output_folder, csv_file_path, use_compression, processes_num, tokenized):
         # CSV to get program data from
        self.csv_file_path = csv_file_path

        # Output folder to save data to
        self.output_folder = output_folder

        # Input folder to get ASTs and tokens from
        self.input_folder = input_folder

        self.tokenized = tokenized

        if tokenized:
            self.tokenizers = {}

            for dirs, _, files in os.walk(input_folder):
                for file in files:
                    if 'tokens.json' in file:
                        self.tokenizers[file.split('_')[0]] = Tokenizer(output_folder, self.tokenized)
                        self.tokenizers[file.split('_')[0]].load(os.path.join(dirs, file))

            # Create reserved label tokenizer
            # self.res_tn = Tokenizer(output_folder, self.tokenized)
            # self.res_tn.load(input_folder + 'RES_tokens.json')

            # # Create non reserved label tokenizer
            # self.tn = Tokenizer(output_folder, self.tokenized)
            # self.tn.load(input_folder + 'tokens.json')

        # Create JSON importer
        self.importer = JsonImporter()

        # Boolean indicating whether ASTs from the input folder are stored using compression
        self.use_compression = use_compression

        # Number of parallel processes
        self.processes_num = processes_num


    def get_label(self, node):
        if self.tokenized:
            if node.res:
                return self.tokenizers['RES'].get_label(node.token)
            else:
                parent_label = self.tokenizers['RES'].get_label(node.parent.token)
                if 'LITERAL' in parent_label:   
                    return self.tokenizers['LITERAL'].get_label(node.token)      
                elif 'TYPE' == parent_label:
                    return self.tokenizers['TYPE'].get_label(node.token)
                else:
                    return self.tokenizers['NAME'].get_label(node.token)
        else:
            return node.token

    def merge_terminals(self, terminals):
        return ' '.join([self.get_label(term) for term in terminals])

    def get_operator(self, ast_item):
        operator = self.get_label(ast_item).split('_')[-1]
        code = ''
        if 'BINARY' in self.get_label(ast_item) or 'COMPOUND_ASSIGNMENT' in self.get_label(ast_item):
            code += self.parse_node(ast_item.children[0])
            code += f' {operator} '
            code += self.parse_node(ast_item.children[1])
        elif 'UNARY' in self.get_label(ast_item):
            if 'POST' in self.get_label(ast_item):
                code += self.parse_node(ast_item.children[0])
                code += operator
            else:
                code += operator + ' '
                code += self.parse_node(ast_item.children[0])
        elif 'CONDITIONAL_OPERATOR' == self.get_label(ast_item):
            code += self.parse_node(ast_item.children[0])
            code += ' ? '
            code += self.parse_node(ast_item.children[1])
            code += ':'
            code += self.parse_node(ast_item.children[2])
        else:
            print(ast_item)
            pass



        return code


    def get_call_exp_operator(self, ast_item):
        code = ''
        operator_label = self.get_label(ast_item.children[0].children[0])
        operator = operator_label.split('operator')[-1]

        if operator == '[]':
            code += self.parse_node(ast_item.children[1].children[0])
            code += f'[{self.parse_node(ast_item.children[1].children[1])}]'
        elif operator == '()':
            code += self.parse_node(ast_item.children[1].children[0])
            if len(ast_item.children[1].children) > 1:
                code += f'({self.parse_node(ast_item.children[1].children[1])})'
            else:
                code += '()'
        elif operator == '*' or len(ast_item.children[1].children) < 2:
            code += operator
            code += self.parse_node(ast_item.children[1].children[0])
        elif operator in ['++_PRE', '++_POST', '--_PRE', '--_POST']:
            if 'PRE' in operator:
                code += operator.split('_')[0]
                code += self.parse_node(ast_item.children[1].children[0])
            else:
                code += self.parse_node(ast_item.children[1].children[0])
                code += operator.split('_')[0]
        else:
            # first argument of operator
            code += self.parse_node(ast_item.children[1].children[0])
            code += f' {operator} '
            code += self.parse_node(ast_item.children[1].children[1])        

        return code


    def get_var_decl(self, ast_item):
        # Contains all non-ref and non-type values
        # e.g. int ch[1][1] = {{2}} would give [1, 1, 2]
        declarations = []
        acc_spec = ''
        var_type = ''

        # If the variable is an array, this is will be filled
        array_sizes = []


        for child in ast_item.children:
            # Skip the type if this is a child of a declaration statement and not the first child
            #  and the type is the same as the type of the first child
            if self.get_label(child) == 'TYPE_KIND' and \
            not (self.get_label(ast_item.parent) == 'DECL_STMT' \
                and ast_item != ast_item.parent.children[0]):
                var_type_size = self.get_type(child.children[0])

                if type(var_type_size) is tuple:
                    var_type += var_type_size[0]
                    array_sizes = var_type_size[1]
                else:
                    var_type = var_type_size
            elif self.get_label(child) == 'TYPE_KIND':
                var_type_size = self.get_type(child.children[0])

                if type(var_type_size) is tuple:
                    array_sizes = var_type_size[1]

              
            elif self.get_label(child) == 'DECLARATOR':
                for decl_child in child.children:
                    if self.get_label(decl_child) == 'NAME':
                        var_name = self.merge_terminals(decl_child.children)
                    else:
                        declarations.append(self.parse_node(decl_child))
            elif self.get_label(child) == 'ACCESS_SPECIFIER':
                acc_spec += f'{self.merge_terminals(child.children).lower()}:\n'        

        ref_dims = ['[' + num + ']' for num in array_sizes]

        # initialize value the variable was initialized to (empty)
        var_value = ''

        # append initial values if set
        if len(declarations) > 0:
            var_value += ' = ' + ' '.join(declarations)


        # Combine the type of the variable with the name, dimensions and initial value
        return f'{acc_spec}{var_type} {var_name}{"".join(ref_dims)}{var_value}'

    def get_type(self, ast_item):
        type_string = ''

        if self.get_label(ast_item) in ['TYPE', 'TYPE_REF']:
            return self.get_label(ast_item.children[0])

        elif self.get_label(ast_item) == 'TYPE_ARRAY':
            array_sizes = []
            array_type = 'auto'
            for array_child in ast_item.children:
                if self.get_label(array_child) in ['TYPE', 'TYPE_REF', 'TYPE_RECORD']:
                    array_type = self.get_type(array_child)
                elif self.get_label(array_child) == 'ARRAY_SIZES':
                    for array_size in array_child.children:
                        array_sizes.append(self.get_label(array_size.children[0]))

            type_string += array_type

            return (type_string, array_sizes)

        elif self.get_label(ast_item) == 'TYPE_RECORD':
            record_type = 'auto'
            for record_child in ast_item.children:
                if self.get_label(record_child) in ['TYPE', 'TYPE_REF']:
                    record_type = self.get_type(record_child)   

            type_string += record_type

            for record_child in ast_item.children:                       
                if self.get_label(record_child) == 'TYPE_RECORD_ELEMENTS':
                    type_string += '<'
                    for index, record_element in enumerate(record_child.children):
                        type_string += self.get_type(record_element)

                        if index < len(record_child.children)- 1:
                            type_string += ', '

                    type_string += '>'

            
            return type_string

        elif self.get_label(ast_item) == 'LVALUEREFERENCE':
            return self.get_type(ast_item.children[0]) + '&'

        elif self.get_label(ast_item) == 'RVALUEREFERENCE':
            return self.get_type(ast_item.children[0]) + '&&'

                            
                    


    def get_function_decl(self, ast_item):
        params = []
        acc_spec = ''
        return_type = ''
        const = ''
        for child in ast_item.children:
            if self.get_label(child) == 'TYPE_KIND':
                return_type += self.get_type(child.children[0])
            elif self.get_label(child) == 'PARM_DECL':
                params.append(self.get_var_decl(child))
            elif self.get_label(child) == 'NAME':
                func_name = self.merge_terminals(child.children)
            elif self.get_label(child) == 'ACCESS_SPECIFIER':
                acc_spec += f'{self.get_label(child.children[0]).lower()}:\n'
            elif self.get_label(child) == 'CONST':
                const += ' const'

        
        return f'{acc_spec}{return_type} {func_name}({", ".join(params)}){const}'

    def is_function(self, node):
        return self.get_label(node) in ['FUNCTION_DECL', 'FUNCTION_TEMPLATE',
                            'CXX_METHOD', 'DESTRUCTOR', 'CONSTRUCTOR']


    def get_temp_type_param(self, ast_item):
        parameter_pack = False
        # If it is the last template type parameter, check if we need to add ... (=parameter pack -> zero or more params)
        if ast_item == ast_item.parent.children[-1]:
            function_decl_index = -1
            for index, child in enumerate(ast_item.parent.parent.children):
                if child == ast_item.parent:
                    function_decl_index = index + 1

            if len(ast_item.parent.children) > function_decl_index and len(ast_item.parent.children[function_decl_index].children) > 1:
                last_parm_decl = ast_item.parent.parent.children[function_decl_index].children[-2].children[0].children[0]
                if self.get_label(last_parm_decl).endswith('...'):
                    parameter_pack = True

        return f'typename{"..." if parameter_pack else ""} {self.get_label(ast_item.children[0])}'


    def get_lambda_expr(self, ast_item):
        capture_clauses = []
        params = []

        for child in ast_item.children:
            if self.get_label(child) == 'CAPTURE_CLAUSE':
                capture_clauses.append(self.merge_terminals(child.children))
            elif self.get_label(child) == 'PARM_DECL':
                params.append(self.get_var_decl(child))

        
        return f'[{", ".join(capture_clauses)}]({", ".join(params)})'


    def parse_node(self, node):
        call_exp_operators = ['[]', '=', '<<', '>>', '==', '+', '-', '%', '*', '/',
                             '+=', '-=', '^=', '||', '()', '!=',
                             '++_PRE', '++_POST', '--_PRE', '--_POST']

        call_exp_operator_labels = ['operator' + op for op in call_exp_operators]
        code = ''

        if self.get_label(node) == 'VAR_DECL' or self.get_label(node) == 'FIELD_DECL' or self.get_label(node) == 'UNEXPOSED_DECL':
            code += self.get_var_decl(node)
        elif self.is_function(node):
            code += self.get_function_decl(node)
            for child in node.children:
                code += self.parse_node(child)
        elif self.get_label(node) == 'COMPOUND_STMT':
            code += ' {\n'
            for child in node.children:
                code += self.parse_node(child)
            code += '}\n'
        elif self.get_label(node) == 'PAREN_EXPR':
            code += '('
            for child in node.children:
                code += self.parse_node(child)
            code += ')'
        elif 'OPERATOR' in self.get_label(node) or 'UNARY_EXPR' in self.get_label(node):
            code += self.get_operator(node)
        elif self.get_label(node) == 'GNU_NULL_EXPR':
            code += 'NULL'
        elif self.get_label(node) == 'CXX_NULL_PTR_LITERAL_EXPR':
            code += 'nullptr'
        elif self.get_label(node) == 'COMPOUND_LITERAL_EXPR' or self.get_label(node) == 'CSTYLE_CAST_EXPR':
            code += '('
            code += self.parse_node(node.children[0]) if self.get_label(node) == 'COMPOUND_LITERAL_EXPR' else self.get_type(node.children[0].children[0])
            code += ')'
            for child in node.children[1:]:
                code += self.parse_node(child)
        elif self.get_label(node) in ['DECL_REF_EXPR', 'MEMBER_REF_EXPR', 'MEMBER_REF', 'LABEL_REF'] or 'LITERAL' in self.get_label(node):
            for child in node.children[1:]:
                code += self.parse_node(child)

            if self.get_label(node) == 'MEMBER_REF_EXPR' and len(node.children) > 1 \
                and self.get_label(node.children[1]) != 'CXX_THIS_EXPR': #node.parent.parent) == 'REF':
                code += '.'

            code += self.get_label(node.children[0])


        elif self.get_label(node) == 'IF_STMT':
            code += 'if('
            # The first compound statement of an if statement is the code of the
            # if statement, the second (and also last) compound statement is for
            # a possible else statement
            compound_statements = 0
            for index, child in enumerate(node.children):
                if index == len(node.children) - 1 and compound_statements > 0:
                    code += 'else '
                if self.get_label(child) == 'COMPOUND_STMT':
                    compound_statements += 1

                code += self.parse_node(child)

                if index == 0:
                    code += ')'

        elif self.get_label(node) == 'ARRAY_SUBSCRIPT_EXPR':
            code += self.parse_node(node.children[0])
            code += '['
            code += self.parse_node(node.children[1])
            code += ']'
        elif self.get_label(node) == 'RETURN_STMT':
            code += 'return'
            for child in node.children:
                code += ' '
                code += self.parse_node(child)
        elif self.get_label(node) == 'FOR_STMT':
            code += 'for('

            # Count amount of expressions in for loop (can essentialy be empty: for(;;))
            for_stmt_expressions = 0

            for child in node.children:
                if self.get_label(child) != 'COMPOUND_STMT':
                    for_stmt_expressions += 1
                else:
                    break

            # add ; for empty expressions e.g. if we have 2 expressions: for(;expr2;expr3)
            for _ in range(3 - for_stmt_expressions):
                code += ';'

            # add expressions
            for i in range(for_stmt_expressions):
                code += self.parse_node(node.children[i])
                if i < for_stmt_expressions - 1:
                    code += '; '
            code += ')'

            # parse for loop compound statement
            for i in range(for_stmt_expressions, len(node.children)):
                code += self.parse_node(node.children[i])
        elif self.get_label(node) == 'CALL_EXPR':
            if self.get_label(node.children[0].children[0]) in call_exp_operator_labels:
                code += self.get_call_exp_operator(node)

            else:
                for child in node.children:
                    if self.get_label(child) != 'NAME' and self.get_label(child) != 'ARGUMENTS':
                        code += self.parse_node(child)
                        if self.get_label(child) != 'TYPE_REF':
                            code += '.'

                for child in node.children:
                    if self.get_label(child) == 'NAME':
                        code += self.merge_terminals(child.children) + '('
                    elif self.get_label(child) == 'ARGUMENTS':
                        for index, arg in enumerate(child.children):
                            code += self.parse_node(arg)
                            if index < len(child.children) - 1:
                                code += ', '
                code += ')'
        
        elif self.get_label(node) == 'TYPEDEF_DECL':
            for child in node.children:
                if self.get_label(child) == 'TYPE_DEF':
                    code += f'typedef {self.get_type(child.children[0].children[0])} '
                elif self.get_label(child) == 'IDENTIFIER':
                    code += self.get_label(child.children[0])

        elif self.get_label(node) == 'WHILE_STMT':
            code += 'while('
            code += self.parse_node(node.children[0])
            code += ')'
            code += self.parse_node(node.children[1])

        elif self.get_label(node) == 'TYPE_REF' or self.get_label(node) == 'TYPE':
            code += self.get_type(node)
            if self.get_label(node.parent) != 'COMPOUND_LITERAL_EXPR' and not 'CAST' in self.get_label(node.parent):
                code += '::'

        elif self.get_label(node) == 'CLASS_DECL':
            code += 'class '
            for child in node.children:
                if self.get_label(child) == 'NAME':
                    code += self.merge_terminals(child.children)
                else:
                    code += self.parse_node(child)

        elif self.get_label(node) == 'STRUCT_DECL':
            code += 'struct '
            for child in node.children:
                if self.get_label(child) == 'NAME':
                    code += self.merge_terminals(child.children)
                else:
                    code += self.parse_node(child)

        elif self.get_label(node) in ['BREAK_STMT', 'CONTINUE_STMT']:
            code += self.get_label(node).split('_')[0].lower()
        elif self.get_label(node) == 'CXX_FOR_RANGE_STMT':
            code += 'for('
            code += self.parse_node(node.children[0])
            code += ':'
            code += self.parse_node(node.children[1])
            code += ')'

            for child in node.children[2:]:
                code += self.parse_node(child)

        elif self.get_label(node) == 'INIT_LIST_EXPR':
            code += '{'
            for index, child in enumerate(node.children):
                code += self.parse_node(child)
                if index < len(node.children) - 1:
                    code += ','
            code += '}'
        elif self.get_label(node) == 'DECL_STMT':
            for index, child in enumerate(node.children):
                code += self.parse_node(child)
                if index < len(node.children) - 1:
                    code += ','
        elif self.get_label(node) == 'TEMPLATE_DECL':
            code += 'template<'
            for index, child in enumerate(node.children):
                code += self.parse_node(child)
                if index < len(node.children) - 1:
                    code += ','
            code += '>\n'

        elif self.get_label(node) == 'TEMPLATE_TYPE_PARAMETER':
            code += self.get_temp_type_param(node)
        elif self.get_label(node) == 'CXX_FUNCTIONAL_CAST_EXPR':
            code += f'{self.get_label(node.children[0].children[0])}('
            for child in node.children[1:]:
                code += self.parse_node(child)
            
            code += ')'

        elif self.get_label(node) == 'CONSTRUCTOR_INITIALIZER':
            constr_inits = []

            for child in node.parent.children:
                if self.get_label(child) == 'CONSTRUCTOR_INITIALIZER':
                    constr_inits.append(child)

            # If first constr init, add ' : '
            if node == constr_inits[0]:
                code += ' : '
            
            code += self.parse_node(node.children[0]) + '('
            if len(node.children) > 1:
                code += self.parse_node(node.children[1])
            code += ')'

            # If not last constr init, place comma in between constr inits
            if node != constr_inits[-1]:
                code += ', '

        elif self.get_label(node) == 'PACK_EXPANSION_EXPR':
            for child in node.children:
                code += self.parse_node(child)
            code += '...'

        elif self.get_label(node) == 'CXX_THIS_EXPR':
            code += 'this->'


        elif self.get_label(node) == 'SWITCH_STMT':
            code += 'switch('
            code += self.parse_node(node.children[0])
            code += ')'
            for child in node.children[1:]:
                code += self.parse_node(child)

        elif self.get_label(node) == 'CASE_STMT':
            code += 'case '
            code += self.parse_node(node.children[0])
            code += ':\n'
            for child in node.children[1:]:
                code += self.parse_node(child)


        elif self.get_label(node) == 'CXX_TRY_STMT':
            code += 'try'
            for child in node.children:
                code += self.parse_node(child)

        elif self.get_label(node) == 'CXX_CATCH_STMT':
            if len(node.children) < 2:
                code += 'catch(...)'
                for child in node.children:
                    code += self.parse_node(child)
            
            else:
                code += 'catch('
                code += self.parse_node(node.children[0])
                code += ')'
                for child in node.children[1:]:
                    code += self.parse_node(child)

        elif self.get_label(node) == 'LAMBDA_EXPR':
            code += self.get_lambda_expr(node)
            for child in node.children:
                code += self.parse_node(child)

        elif self.get_label(node) == 'CXX_STATIC_CAST_EXPR':
            code += f'static_cast<{self.get_label(node.children[0].children[0])}>('
            for child in node.children[1:]:
                code += self.parse_node(child)

            code += ')'


        elif self.get_label(node) == 'DO_STMT':
            code += 'do'
            code += self.parse_node(node.children[0])
            code += 'while('
            for child in node.children[1:]:
                code += self.parse_node(child)
            code += ')'

        elif self.get_label(node) == 'GOTO_STMT':
            code += 'goto '
            for child in node.children:
                code += self.parse_node(child)

        elif self.get_label(node) == 'LABEL_STMT':
            code += f'{self.get_label(node.children[0])}:\n'
            for child in node.children[1:]:
                code += self.parse_node(child)

        # elif self.get_label(node) == 'TYPE_KIND':
        #     code += self.get_type(node.children[0])
        #     print(node.parent, node.children[0].children)

        else:
            # print(self.get_label(node))
            pass

        if ('COMPOUND_STMT' in self.get_label(node.parent) \
        or self.get_label(node.parent) == 'root' \
        # If statement one-liner with no compound statement (= {..}), we still want ";" after each line
        or (self.get_label(node.parent) == 'IF_STMT' \
        and 'COMPOUND_STMT' not in [self.get_label(c) for c in node.parent.children] \
        and node != node.parent.children[0])) \
        and (self.get_label(node) != 'FUNCTION_DECL' \
        and self.get_label(node) != 'IF_STMT' \
        and self.get_label(node) != 'FOR_STMT' \
        and self.get_label(node) != 'CXX_FOR_RANGE_STMT' \
        and self.get_label(node) != 'WHILE_STMT' \
        and self.get_label(node) != 'TEMPLATE_DECL') \
        or (self.get_label(node) == 'FUNCTION_DECL' and 'COMPOUND_STMT' not in [self.get_label(c) for c in node.children]):
            code += ';\n'

        return code


    def thread_parser(self, file_queue, pbar, output_folder, imports):
        while not file_queue.empty():
            ast_id, ast = file_queue.get()

            root = self.importer.import_(ast)

            output =  open(f'{output_folder}{ast_id}.cpp', 'w')
                
            # try:
            for child in root.children:
                output.write(self.parse_node(child))
            # except Exception as e:
            #     print(f'File: {ast_id} failed: {e}')
            #     pbar.update()
            #     file_queue.task_done()
            #     output.close()
            #     continue

            output.close()

            # print(imports.keys())
            try:
                imports_file = imports[int(ast_id)]
                imports_file = [ele for ele in imports_file[1:-1].split("'") if ele != '' and ele != ', ']
            except KeyError:
                imports_file = []

            # This is not always added but sometimes needed e.g.: std::cout is used in original code but we simply use cout
            if 'using namespace std;' not in imports_file:
                imports_file.append('using namespace std;')

            add_includes_usings(f'{output_folder}{ast_id}.cpp', imports_file)
            pbar.update()
            file_queue.task_done()


    def parse_asts_to_code(self):
        file_paths = []

        # Read csv file in chunks (may be very large)
        asts = pd.read_csv(f'{self.input_folder}asts.csv{".bz2" if self.use_compression else ""}', chunksize=1e5)

        # Read metadata file with imports
        print('loading csv file with imports...')
        metadata_file = pd.read_csv(self.csv_file_path, usecols=['solutionId', 'imports'])
        metadata_file = metadata_file.set_index('solutionId')
        imports = metadata_file.to_dict()['imports']
        del metadata_file

        # iterate over the chunks
        for asts_chunk in asts:
            # Create progressbar
            pbar = tqdm(total=len(asts_chunk))
            # Create file queue to store the program data
            file_queue = queue.Queue(len(asts_chunk))

            # Fill the queue with files.
            for ast in list(asts_chunk.iterrows()):
                    file_queue.put((ast[1]['id'], ast[1]['AST']))
        
            pbar = tqdm(total=len(file_paths))

            try:
                threads = []
                # List of files with a non-zero return code.
                for _ in range(self.processes_num):
                    t = threading.Thread(target=self.thread_parser,
                                        args=(file_queue, pbar, self.output_folder, imports))
                    t.daemon = True
                    t.start()
                    threads.append(t)

                # Wait for all threads to be done.
                file_queue.join()
                for thread in threads:
                    thread.join() 
 
            except KeyboardInterrupt:
                os.kill(0, 9)
