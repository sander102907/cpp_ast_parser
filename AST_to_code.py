from anytree.importer import JsonImporter
from anytree import RenderTree
from anytree.search import find
from utils import assignment_operators

importer = JsonImporter()

file = open('ast_parser/tree.json', 'r').read()

root = importer.import_(file)

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
    else:
        # print(ast_item)
        pass



    return code

def get_var_decl(ast_item):
    # Contains all non-ref and non-type values
    # e.g. int ch[1][1] = {{2}} would give [1, 1, 2]
    declarations = []


    for child in ast_item.children:
        if child.label == 'TYPE':
            var_type = child.children[0].label
        elif child.label == 'DECLARATOR':
            for decl_child in child.children:
                if decl_child.label == 'NAME':
                    var_name = decl_child.children[0].label
                else:
                    declarations.append(parse_node(decl_child))

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
    return f'{var_type} {var_name}{"".join(ref_dims)}{var_value}'


def get_function_decl(ast_item):
    params = []
    for child in ast_item.children:
        if child.label == 'RETURN_TYPE':
            return_type = child.children[0].label
        elif child.label == 'PARM_DECL':
            params.append(get_var_decl(child))
        elif child.label == 'NAME':
            func_name = child.children[0].label

    
    return f'{return_type} {func_name}({", ".join(params)})'

def parse_node(node):
    code = ''

    if node.label == 'VAR_DECL':
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
    elif node.label == 'REF' or 'LITERAL' in node.label:
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
        if '>>' in node.children[0].children[0].label \
        or '<<' in node.children[0].children[0].label:
            # first argument of operator >>/<<
            code += parse_node(node.children[1].children[0])
            code += ' >> ' if '>>' in node.children[0].children[0].label else ' << '
            code += parse_node(node.children[1].children[1])

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

    else:
        # print(node, node.parent, node.children)
        pass

    if ('COMPOUND_STMT' in node.parent.label \
    or node.parent.label == 'root') \
    and (node.label != 'FUNCTION_DECL' \
    and node.label != 'CLASS_DECL' \
    and node.label != 'IF_STMT' \
    and node.label != 'FOR_STMT' \
    and node.label != 'WHILE_STMT'):
        code += ';\n'

    return code
    

output =  open('ast_parser/output.cpp', 'w')
    
for child in root.children:
    output.write(parse_node(child))






