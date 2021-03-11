# cpp_ast_parser

Parser for c++ code to an AST representation and also from the AST back to code. 

## Requirements

The parser should work fine for any version of python 3. Before using `main.py` install the requirements (setting up a virtual environment first is recommended):

```pip3 install -r requirements.txt```

## Usage

The `main.py` file is the main utility from which the AST parser can be run to parse C++ code to ASTs and from ASTs back to c++ code.

Running the AST parser will produce the following in the selected output folder:
- AST trees in JSON format (compressed by default using .gz)
- tokens.json -> A json dictionary containing token (id) and code pairs of user defined tokens (variable names, function names, etc.)
- reserved_tokens.json -> A json dictionary containing token (id) and code pairs of reserved c++ tokens (operators, function declaration, etc.)

It has the following command line interface:

```
usage: main.py [-h] -csv csv_file_path -o output_folder [-i input_folder] [-c use_compression] [-l libclang-path] method

positional arguments:
  method                The parse method: AST or code

optional arguments:
  -h, --help            show this help message and exit
  -csv csv_file_path, --csv_file_path csv_file_path
                        the path to the CSV file containing data of c++ programs
  -o output_folder, --output_folder output_folder
                        the output folder to the data to
  -i input_folder, --input_folder input_folder
                        the input folder with AST json files to parse to code
  -c use_compression, --use-compression use_compression
                        Use compression for the ASTs
  -l libclang-path, --libclang libclang-path
                        path to clang library libclang.so file

```

A CSV file is used to read the code of the C++ programs (this is much faster than possibly millions of I/O operations on reading seperate files). This CSV file can either be created manually or it can be created with the `merge_solutions_metadata_code` from [this](https://github.com/sander102907/codeforces-scraper) repository and then using the `preprocess_files.py` file in this repository on the CSV. 

The CSV file should contain the following columns (note that since this is originally meant for code competition solutions dataset, the term solution is used often):
- solutionId (can be a program name or ID)
- solution (The actual c++ code)
- imports (The using and includes of the C++ file, for example: `#include<bits/stdc++.h>` and `using namespace std;`)

## Example

To create ASTs from a CSV file with C++ programs, this is an example of how to run the program:\
```python3 main.py AST -csv ../data/cpp_preprocessed/test.csv -o ../data/ast_trees/ -l /usr/lib/x86_64-linux-gnu/libclang-6.0.so.1```

To set the CSV input file, the output folder to save the AST trees and the clang library file path.

To parse ASTs back to the C++ programs, this is an example of how to run the program:\
```python3 main.py code -csv ../data/cpp_preprocessed/test.csv -i ../data/ast_trees/ -o ../data/ast_trees_to_code/ -l /usr/lib/x86_64-linux-gnu/libclang-6.0.so.1```

To set the CSV used for setting back the imports, the input folder containing the ASTs, the output folder to store the C++ programs and the clang library file path.



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
    }
  ]
}
```

