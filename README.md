# cpp_ast_parser

Parser for c++ code to an AST representation and also from the AST back to code. 


## Example

### A C++ program containing a simple add function
```
// program to add two numbers using a function

#include <iostream>

using namespace std;

// declaring a function
int add(int a, int b) {
    return (a + b);
}
```

### The AST (plotting is not 100% correct yet, no duplicate labels)
![tree](https://user-images.githubusercontent.com/22891388/110127486-007b2880-7dc6-11eb-88b5-90703fc7d8e0.png)


### The AST in JSON representation

```
{
  "label": "root",
  "is_reserved": true,
  "children": [
    {
      "label": "FUNCTION_DECL",
      "is_reserved": true,
      "children": [
        {
          "label": "NAME",
          "is_reserved": true,
          "children": [
            {
              "label": "add",
              "is_reserved": false
            }
          ]
        },
        {
          "label": "RETURN_TYPE",
          "is_reserved": true,
          "children": [
            {
              "label": "int",
              "is_reserved": false
            }
          ]
        },
        {
          "label": "PARM_DECL",
          "is_reserved": true,
          "children": [
            {
              "label": "TYPE",
              "is_reserved": true,
              "children": [
                {
                  "label": "int",
                  "is_reserved": false
                }
              ]
            },
            {
              "label": "DECLARATOR",
              "is_reserved": true,
              "children": [
                {
                  "label": "NAME",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "a",
                      "is_reserved": false
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "label": "PARM_DECL",
          "is_reserved": true,
          "children": [
            {
              "label": "TYPE",
              "is_reserved": true,
              "children": [
                {
                  "label": "int",
                  "is_reserved": false
                }
              ]
            },
            {
              "label": "DECLARATOR",
              "is_reserved": true,
              "children": [
                {
                  "label": "NAME",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "b",
                      "is_reserved": false
                    }
                  ]
                }
              ]
            }
          ]
        },
        {
          "label": "COMPOUND_STMT",
          "is_reserved": true,
          "children": [
            {
              "label": "RETURN_STMT",
              "is_reserved": true,
              "children": [
                {
                  "label": "PAREN_EXPR",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "BINARY_OPERATOR_+",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "DECL_REF_EXPR",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "a",
                              "is_reserved": false
                            }
                          ]
                        },
                        {
                          "label": "DECL_REF_EXPR",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "b",
                              "is_reserved": false
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "label": "FUNCTION_DECL",
      "is_reserved": true,
      "children": [
        {
          "label": "NAME",
          "is_reserved": true,
          "children": [
            {
              "label": "main",
              "is_reserved": false
            }
          ]
        },
        {
          "label": "RETURN_TYPE",
          "is_reserved": true,
          "children": [
            {
              "label": "int",
              "is_reserved": false
            }
          ]
        },
        {
          "label": "COMPOUND_STMT",
          "is_reserved": true,
          "children": [
            {
              "label": "DECL_STMT",
              "is_reserved": true,
              "children": [
                {
                  "label": "VAR_DECL",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "TYPE",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "int",
                          "is_reserved": false
                        }
                      ]
                    },
                    {
                      "label": "DECLARATOR",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "NAME",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "sum",
                              "is_reserved": false
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "label": "BINARY_OPERATOR_=",
              "is_reserved": true,
              "children": [
                {
                  "label": "DECL_REF_EXPR",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "sum",
                      "is_reserved": false
                    }
                  ]
                },
                {
                  "label": "CALL_EXPR",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "NAME",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "add",
                          "is_reserved": false
                        }
                      ]
                    },
                    {
                      "label": "ARGUMENTS",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "INTEGER_LITERAL",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "100",
                              "is_reserved": false
                            }
                          ]
                        },
                        {
                          "label": "INTEGER_LITERAL",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "78",
                              "is_reserved": false
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "label": "CALL_EXPR",
              "is_reserved": true,
              "children": [
                {
                  "label": "NAME",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "operator<<",
                      "is_reserved": false
                    }
                  ]
                },
                {
                  "label": "ARGUMENTS",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "CALL_EXPR",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "NAME",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "operator<<",
                              "is_reserved": false
                            }
                          ]
                        },
                        {
                          "label": "ARGUMENTS",
                          "is_reserved": true,
                          "children": [
                            {
                              "label": "CALL_EXPR",
                              "is_reserved": true,
                              "children": [
                                {
                                  "label": "NAME",
                                  "is_reserved": true,
                                  "children": [
                                    {
                                      "label": "operator<<",
                                      "is_reserved": false
                                    }
                                  ]
                                },
                                {
                                  "label": "ARGUMENTS",
                                  "is_reserved": true,
                                  "children": [
                                    {
                                      "label": "DECL_REF_EXPR",
                                      "is_reserved": true,
                                      "children": [
                                        {
                                          "label": "cout",
                                          "is_reserved": false
                                        }
                                      ]
                                    },
                                    {
                                      "label": "STRING_LITERAL",
                                      "is_reserved": true,
                                      "children": [
                                        {
                                          "label": "\"100 + 78 = \"",
                                          "is_reserved": false
                                        }
                                      ]
                                    }
                                  ]
                                }
                              ]
                            },
                            {
                              "label": "DECL_REF_EXPR",
                              "is_reserved": true,
                              "children": [
                                {
                                  "label": "sum",
                                  "is_reserved": false
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "label": "DECL_REF_EXPR",
                      "is_reserved": true,
                      "children": [
                        {
                          "label": "endl",
                          "is_reserved": false
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "label": "RETURN_STMT",
              "is_reserved": true,
              "children": [
                {
                  "label": "INTEGER_LITERAL",
                  "is_reserved": true,
                  "children": [
                    {
                      "label": "0",
                      "is_reserved": false
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

