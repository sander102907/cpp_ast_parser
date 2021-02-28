
from anytree import NodeMixin

"""
Custom tree node for the anytree module to contain
- label: name of the node (the actual data)
- is_reserved: whether it is a reserved label from the C++ language or user defined
- parent: the parent node
- children: the children nodes
"""

class Node(NodeMixin): 
    def __init__(self, label, is_reserved, parent=None, children=None):
        super(Node, self).__init__()
        self.label = label
        self.is_reserved = is_reserved
        self.parent = parent
        if children:
            self.children = children
            
    def __str__(self):
        return self.label