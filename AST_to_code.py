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
import json
import re

def get_operator(ast_item):
    operator = ast_item.label.split('_')[-1]
    code = ''
    if 'BINARY' in ast_item.label or 'COMPOUND_ASSIGNMENT' in ast_item.label:
        code += parse_node(ast_item.children[0])
        code += f' {operator} '
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

call_exp_operators = ['[]', '=', '<<', '>>', '==', '+', '-', '%', '*', '/', '+=', '-=', '^=']
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
        #  and the type is the same as the type of the first child
        if child.label == 'TYPE' and \
        not (ast_item.parent.label == 'DECL_STMT' \
            and ast_item != ast_item.parent.children[0] \
            and ast_item.parent.children[0].children[0].children[0].label == child.children[0].label):
            if ast_item.parent.label == 'DECL_STMT' and \
                ast_item.parent.children[0].children[0].children[0].label != child.children[0].label:
                print(child.children[0].label)
                var_type += ''.join(re.findall(r'\[.*\]', child.children[0].label))
            else:
                var_type += child.children[0].label
        elif child.label == 'DECLARATOR':
            for decl_child in child.children:
                if decl_child.label == 'NAME':
                    var_name = decl_child.children[0].label
                else:
                    declarations.append(parse_node(decl_child))
        elif child.label == 'ACCESS_SPECIFIER':
            acc_spec += f'{child.children[0].label.lower()}:\n'


    # get ref dims from type so e.g. int x[50][20] -> ['[50]', '[20]']
    ref_dims = re.findall(r'\[[^\[\]]*\]', var_type)

     # Get number if dimensions -> e.g. ch[1][1] has 2 dimensions
    dimensions = len(ref_dims)

    # bitset<N> bs[N]; -> Has two declarations of N, first is for <N> second is dimension, we do not need the <..> declarations
    type_args = []
    for el in re.findall(r'<[^<>]*>', var_type):
        type_args += el.replace('<', '').replace('>', '').split(',')

    for decl in declarations:
        for arg in type_args:
            if decl in arg:
                type_args.remove(arg)
                declarations.remove(decl)
                break
    

    # ref_dims = ['[' + num + ']' for num in declarations[:dimensions][::-1]]


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
    return_type = ''
    const = ''
    for child in ast_item.children:
        if child.label == 'RETURN_TYPE':
            return_type += child.children[0].label
        elif child.label == 'PARM_DECL':
            params.append(get_var_decl(child))
        elif child.label == 'NAME':
            func_name = child.children[0].label
        elif child.label == 'ACCESS_SPECIFIER':
            acc_spec += f'{child.children[0].label.lower()}:\n'
        elif child.label == 'CONST':
            const += ' const'

    
    return f'{acc_spec}{return_type} {func_name}({", ".join(params)}){const}'

def parse_node(node):
    code = ''

    if node.label == 'VAR_DECL' or node.label == 'FIELD_DECL' or node.label == 'UNEXPOSED_DECL':
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
    elif 'OPERATOR' in node.label or 'UNARY_EXPR' in node.label:
        code += get_operator(node)
    elif node.label == 'GNU_NULL_EXPR':
        code += 'NULL'
    elif node.label == 'CXX_NULL_PTR_LITERAL_EXPR':
        code += 'nullptr'
    elif node.label == 'COMPOUND_LITERAL_EXPR' or node.label == 'CSTYLE_CAST_EXPR':
        code += '('
        code += parse_node(node.children[0])
        code += ')'
        for child in node.children[1:]:
            code += parse_node(child)
    elif node.label in ['DECL_REF_EXPR', 'MEMBER_REF_EXPR'] or 'LITERAL' in node.label:
        for child in node.children[0].children:
            code += parse_node(child)

        if node.label == 'MEMBER_REF_EXPR' and len(node.children[0].children) > 0: #node.parent.parent.label == 'REF':
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

        # Count amount of expressions in for loop (can essentialy be empty: for(;;))
        for_stmt_expressions = 0

        for child in node.children:
            if child.label != 'COMPOUND_STMT':
                for_stmt_expressions += 1
            else:
                break

        # add ; for empty expressions e.g. if we have 2 expressions: for(;expr2;expr3)
        for _ in range(3 - for_stmt_expressions):
            code += ';'

        # add expressions
        for i in range(for_stmt_expressions):
            code += parse_node(node.children[i])
            if i < for_stmt_expressions - 1:
                code += '; '
        code += ')'

        # parse for loop compound statement
        for i in range(for_stmt_expressions, len(node.children)):
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
        code += node.children[0].label
        if node.parent.label != 'COMPOUND_LITERAL_EXPR' and not 'CAST' in node.parent.label:
            code += '::'

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
    elif node.label == 'CXX_FUNCTIONAL_CAST_EXPR':
        for child in node.children:
            code += parse_node(child)
    else:
        # print(node.label)
        pass

    if ('COMPOUND_STMT' in node.parent.label \
    or node.parent.label == 'root' \
    # If statement one-liner with no compound statement (= {..}), we still want ";" after each line
    or (node.parent.label == 'IF_STMT' \
    and 'COMPOUND_STMT' not in [c.label for c in node.parent.children] \
    and node != node.parent.children[0])) \
    and (node.label != 'FUNCTION_DECL' \
    and node.label != 'IF_STMT' \
    and node.label != 'FOR_STMT' \
    and node.label != 'CXX_FOR_RANGE_STMT' \
    and node.label != 'WHILE_STMT' \
    and node.label != 'TEMPLATE_DECL') \
    or (node.label == 'FUNCTION_DECL' and 'COMPOUND_STMT' not in [c.label for c in node.children]):
        code += ';\n'

    return code


def thread_parser(file_queue, pbar, output_folder, importer, includes_usings):
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

        add_includes_usings(f'{output_folder}{file_name.split(".")[0]}.cpp', includes_usings[str(file_name.split(".")[0])])

        pbar.update()
        file_queue.task_done()

# Work with threads to increase the speed
max_task = multiprocessing.cpu_count()
file_paths = []
input_folder = '../data/subset/ast_trees/'
output_folder = '../data/subset/ast_trees_to_code/'

for dirs,_,files in os.walk(input_folder):
    # Create folder to save data if it does not exist yet
    os.makedirs(f'{output_folder}{dirs}', exist_ok=True)
    for f in files:
    	file_paths.append(dirs + f)
 
pbar = tqdm(total=len(file_paths))
file_queue = queue.Queue(max_task)
importer = JsonImporter()

f_in = open('imports.json', 'r')
usings_includes = json.load(f_in)


try:
    task_queue = queue.Queue(max_task)
    # List of files with a non-zero return code.
    failed_files = []
    lock = threading.Lock()
    for _ in range(max_task):
        t = threading.Thread(target=thread_parser,
                            args=(file_queue, pbar, output_folder, importer, usings_includes))
        t.daemon = True
        t.start()

    # Fill the queue with files.
    for f in file_paths:
        file_queue.put(f)

    # Wait for all threads to be done.
    file_queue.join()
    f_in.close

except KeyboardInterrupt:
    os.kill(0, 9)






