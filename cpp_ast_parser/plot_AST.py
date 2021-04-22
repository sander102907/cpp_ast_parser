from __future__ import print_function
import json
import sys

# Tree in JSON format
s = '{"Harry": {"children": ["Bill", {"Jane": {"children": [{"Diane": {"children": ["Mary"]}}, "Mark"]}}]}}'

with open('../data/subset/ast_trees/test.json', 'r') as tree:
    # Convert JSON tree to a Python dict
    data = json.load(tree)

    # Convert back to JSON & print to stderr so we can verify that the tree is correct.
    print(json.dumps(data, indent=4), file=sys.stderr)

    # Extract tree edges from the dict
    edges = []

    def get_edges(treedict, parent=None):
        # if parent is not None:
        #     edges.append((parent, treedict['label']))
        if 'children' in treedict:
            for item in treedict["children"]:
                    get_edges(item, parent=treedict['label'])
                    edges.append((treedict['label'], item['label']))

    get_edges(data)

    with open('tree.dot', 'w') as dot:
        # Dump edge list in Graphviz DOT format
        dot.write('strict digraph tree {\n')
        for row in edges:
            dot.write('    "{0}" -> "{1}";\n'.format(*row))
        dot.write('}')