from anytree.importer import JsonImporter
from anytree import RenderTree
from anytree.search import find
from utils import assignment_operators
from tidy_files import add_includes_usings
import threading
import multiprocessing
import queue as queue
import os
from tqdm import tqdm

def get_operator(ast_item):
    operator = ast_item.label.split('_')[-1]
    code = ''
    if 'BINARY' in ast_item.label or 'COMPOUND_ASSIGNMENT' in ast_item.label:
        code += parse_node(ast_item.children[0])
        code += operator
        code += parse_node(ast_item.children[1])
    elif 'UNARY' in ast_item.label:
        if 'POST' in ast_item.label:
            code += parse_node(ast_item.children[0])
            code += operator
        else:
            code += operator
            code += parse_node(ast_item.children[0])
    elif 'CONDITIONAL_OPERATOR' == ast_item.label:
        code += parse_node(ast_item.children[0])
        code += ' ? '
        code += parse_node(ast_item.children[1])
        code += ':'
        code += parse_node(ast_item.children[2])
    else:
        print(ast_item)
        pass



    return code

call_exp_operators = ['[]', '=', '<<', '>>', '==', '+', '-', '%', '*', '/']
call_exp_operator_labels = ['operator' + op for op in call_exp_operators]


def get_call_exp_operator(ast_item):
    code = ''
    operator_label = ast_item.children[0].children[0].label
    operator = operator_label.split('operator')[-1]

    if operator == '[]':
        code += parse_node(ast_item.children[1].children[0])
        code += f'[{parse_node(ast_item.children[1].children[1])}]'
    elif operator == '*':
        code += operator
        code += parse_node(ast_item.children[1].children[0])
    else:
        # first argument of operator
        code += parse_node(ast_item.children[1].children[0])
        code += f' {operator} '
        code += parse_node(ast_item.children[1].children[1])        

    return code


def get_var_decl(ast_item):
    # Contains all non-ref and non-type values
    # e.g. int ch[1][1] = {{2}} would give [1, 1, 2]
    declarations = []
    acc_spec = ''
    var_type = ''


    for child in ast_item.children:
        # Skip the type if this is a child of a declaration statement and not the first child
        if child.label == 'TYPE' and \
        not (ast_item.parent.label == 'DECL_STMT' and ast_item != ast_item.parent.children[0]):
            var_type += child.children[0].label
        elif child.label == 'DECLARATOR':
            for decl_child in child.children:
                if decl_child.label == 'NAME':
                    var_name = decl_child.children[0].label
                else:
                    declarations.append(parse_node(decl_child))
        elif child.label == 'ACCESS_SPECIFIER':
            acc_spec += f'{child.children[0].label.lower()}:\n'

    # Get number if dimensions -> e.g. ch[1][1] has 2 dimensions
    dimensions = len(var_type.split('[')) - 1

    # Format ref dimensions so e.g. ['2', '6400010'] -> ['[6400010]', '[2]']
    ref_dims = ['[' + num + ']' for num in declarations[:dimensions][::-1]]

    # Format var type (remove dims) e.g. char [40] -> char
    var_type = var_type.split('[')[0].strip()

    # initialize value the variable was initialized to (empty)
    var_value = ''

    # append initial values if set
    if len(declarations[dimensions:]) > 0:
        var_value += ' = ' + ' '.join(declarations[dimensions:])


    # Combine the type of the variable with the name, dimensions and initial value
    return f'{acc_spec}{var_type} {var_name}{"".join(ref_dims)}{var_value}'


def get_function_decl(ast_item):
    params = []
    acc_spec = ''
    for child in ast_item.children:
        if child.label == 'RETURN_TYPE':
            return_type = child.children[0].label
        elif child.label == 'PARM_DECL':
            params.append(get_var_decl(child))
        elif child.label == 'NAME':
            func_name = child.children[0].label
        elif child.label == 'ACCESS_SPECIFIER':
            acc_spec += f'{child.children[0].label.lower()}:\n'

    
    return f'{acc_spec}{return_type} {func_name}({", ".join(params)})'

def parse_node(node):
    code = ''

    if node.label == 'VAR_DECL' or node.label == 'FIELD_DECL':
        code += get_var_decl(node)
    elif node.label == 'FUNCTION_DECL':
        code += get_function_decl(node)
        for child in node.children:
            code += parse_node(child)
    elif node.label == 'COMPOUND_STMT':
        code += ' {\n'
        for child in node.children:
            code += parse_node(child)
        code += '}\n'
    elif node.label == 'PAREN_EXPR':
        code += '('
        for child in node.children:
            code += parse_node(child)
        code += ')'
    elif 'OPERATOR' in node.label:
        code += get_operator(node)
    elif node.label == 'GNU_NULL_EXPR':
        code += 'NULL'
    elif node.label == 'CXX_NULL_PTR_LITERAL_EXPR':
        code += 'nullptr'
    elif node.label in ['DECL_REF_EXPR', 'MEMBER_REF_EXPR'] or 'LITERAL' in node.label:
        for child in node.children[0].children:
            code += parse_node(child)

        if node.label == 'MEMBER_REF_EXPR': #node.parent.parent.label == 'REF':
            code += '.'
        code += node.children[0].label


    elif node.label == 'IF_STMT':
        code += 'if('
        # The first compound statement of an if statement is the code of the
        # if statement, the second (and also last) compound statement is for
        # a possible else statement
        compound_statements = 0
        for index, child in enumerate(node.children):
            if index == len(node.children) - 1 and compound_statements > 0:
                code += 'else '
            if child.label == 'COMPOUND_STMT':
                compound_statements += 1

            code += parse_node(child)

            if index == 0:
                code += ')'

    elif node.label == 'ARRAY_SUBSCRIPT_EXPR':
        code += parse_node(node.children[0])
        code += '['
        code += parse_node(node.children[1])
        code += ']'
    elif node.label == 'RETURN_STMT':
        code += 'return'
        for child in node.children:
            code += ' '
            code += parse_node(child)
    elif node.label == 'FOR_STMT':
        code += 'for('
        for i in range(3):
            code += parse_node(node.children[i])
            if i < 2:
                code += '; '
        code += ')'

        for i in range(3, len(node.children)):
            code += parse_node(node.children[i])
    elif node.label == 'CALL_EXPR':
        if node.children[0].children[0].label in call_exp_operator_labels:
            code += get_call_exp_operator(node)

        else:
            for child in node.children:
                if child.label != 'NAME' and child.label != 'ARGUMENTS':
                    code += parse_node(child)
                    if child.label != 'TYPE_REF':
                        code += '.'

            for child in node.children:
                if child.label == 'NAME':
                    code += child.children[0].label + '('
                elif child.label == 'ARGUMENTS':
                    for index, arg in enumerate(child.children):
                        code += parse_node(arg)
                        if index < len(child.children) - 1:
                            code += ', '
            code += ')'
    
    elif node.label == 'TYPEDEF_DECL':
        for child in node.children:
            if child.label == 'TYPE_DEF':
                code += f'typedef {child.children[0].label} '
            elif child.label == 'IDENTIFIER':
                code += child.children[0].label

    elif node.label == 'WHILE_STMT':
        code += 'while('
        code += parse_node(node.children[0])
        code += ')'
        code += parse_node(node.children[1])

    elif node.label == 'TYPE_REF':
        code += node.children[0].label + '::'

    elif node.label == 'CLASS_DECL':
        code += 'class '
        for child in node.children:
            if child.label == 'NAME':
                code += child.children[0].label
            else:
                code += parse_node(child)

    elif node.label == 'STRUCT_DECL':
        code += 'struct '
        for child in node.children:
            if child.label == 'NAME':
                code += child.children[0].label
            else:
                code += parse_node(child)

    elif node.label in ['BREAK_STMT', 'CONTINUE_STMT']:
        code += node.label.split('_')[0].lower()
    elif node.label == 'CXX_FOR_RANGE_STMT':
        code += 'for('
        code += parse_node(node.children[0])
        code += ':'
        code += parse_node(node.children[1])
        code += ')'

        for child in node.children[2:]:
            code += parse_node(child)

    elif node.label == 'INIT_LIST_EXPR':
        code += '{'
        for index, child in enumerate(node.children):
            code += parse_node(child)
            if index < len(node.children) - 1:
                code += ','
        code += '}'
    elif node.label == 'DECL_STMT':
        for index, child in enumerate(node.children):
            code += parse_node(child)
            if index < len(node.children) - 1:
                code += ','
    elif node.label == 'TEMPLATE_DECL':
        code += 'template<'
        for index, child in enumerate(node.children):
            code += parse_node(child)
            if index < len(node.children) - 1:
                code += ','
        code += '>\n'
    elif node.label == 'TEMPLATE_TYPE_PARAMETER':
        code += f'typename {node.children[0].label}'
    else:
        pass

    if ('COMPOUND_STMT' in node.parent.label \
    or node.parent.label == 'root') \
    and (node.label != 'FUNCTION_DECL' \
    and node.label != 'IF_STMT' \
    and node.label != 'FOR_STMT' \
    and node.label != 'CXX_FOR_RANGE_STMT' \
    and node.label != 'WHILE_STMT' \
    and node.label != 'TEMPLATE_DECL'):
        code += ';\n'

    return code


def thread_parser(file_queue, pbar, output_folder, importer):
     while True:
        file_path = file_queue.get()

        file = open(file_path, 'r').read()

        root = importer.import_(file)

        file_name = file_path.split('/')[-1]

        output =  open(f'{output_folder}{file_name.split(".")[0]}.cpp', 'w')
            
        # try:
        for child in root.children:
            output.write(parse_node(child))
        # except Exception as e:
        #     print(f'File: {file_path} failed: {e}')

        output.close()

        add_includes_usings(f'{output_folder}{file_name.split(".")[0]}.cpp', ['#include <bits/stdc++.h>', 'using namespace std;'])

        pbar.update()
        file_queue.task_done()

# Work with threads to increase the speed
max_task = multiprocessing.cpu_count()
file_paths = ['../data/subset/ast_trees/106395892.json']
input_folder = '../data/subset/ast_trees/'
output_folder = '../data/subset/ast_trees_to_code/'

# for dirs,_,files in os.walk(input_folder):
#     # Create folder to save data if it does not exist yet
#     os.makedirs(f'{output_folder}{dirs}', exist_ok=True)
#     for f in files:
#     	file_paths.append(dirs + f)
 
pbar = tqdm(total=len(file_paths))
file_queue = queue.Queue(max_task)
importer = JsonImporter()


try:
    task_queue = queue.Queue(max_task)
    # List of files with a non-zero return code.
    failed_files = []
    lock = threading.Lock()
    for _ in range(max_task):
        t = threading.Thread(target=thread_parser,
                            args=(file_queue, pbar, output_folder, importer,))
        t.daemon = True
        t.start()

    # Fill the queue with files.
    for f in file_paths:
        file_queue.put(f)

    # Wait for all threads to be done.
    file_queue.join()

except KeyboardInterrupt:
    os.kill(0, 9)






