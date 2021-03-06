import argparse
from cpp_ast_parser.AST_parser import AstParser
from cpp_ast_parser.AST_to_code import AstToCodeParser
from cpp_ast_parser.tester import Tester
import multiprocessing

def main():
    args_parser = argparse.ArgumentParser(
        description='AST parser can create ASTs from CPP code in JSON format and can transform the AST trees back to code')

    args_parser.add_argument('method',
                             metavar='method',
                             type=str,
                             help='The parse method: AST, code or roundtrip',
                             default='AST')

    args_parser.add_argument('-csv', '--csv_file_path',
                             metavar='csv_file_path',
                             type=str,
                             help='the path to the CSV file containing data of c++ programs',
                             required=True)

    args_parser.add_argument('-o', '--output_folder',
                             metavar='output_folder',
                             type=str,
                             help='the output folder to the data to',
                             required=True)

    args_parser.add_argument('-i', '--input_folder',
                             metavar='input_folder',
                             type=str,
                             help='the input folder with AST json files to parse to code',
                             required=False)

    args_parser.add_argument('-s', '--split_terminals',
                             metavar='split_terminals',
                             type=bool,
                             help="""Split terminal labels to clang defined tokens 
                                     (e.g. long long int -> [long, long, int]).
                                     This may greatly reduce the number of unique terminal tokens
                                     if the dataset is large""",
                             required=False,
                             default=True)

    args_parser.add_argument('-t', '--tokenized',
                             metavar='tokenized',
                             type=lambda x: (str(x).lower() == 'true'),
                             help="""Tokenize labels: map labels to integer values. For AST parsing, 
                             the AST tokens will be replaced with the mapped integer values. For AST to code,
                             the tokenized JSON maps will be used for detokenizing to code. If tokenizing is not used,
                             the number of occurences of each label will simply be counted instead. Note that tokenizing
                             will not function properly if the script is run in parallel.""",
                             required=False,
                             default=False)

    args_parser.add_argument('-c', '--use-compression',
                             metavar='use_compression',
                             type=lambda x: (str(x).lower() == 'true'),
                             help='Use compression for the ASTs',
                             required=False,
                             default=True)


    args_parser.add_argument('-l', '--libclang',
                             metavar='libclang-path',
                             type=str,
                             help='path to clang library libclang.so file',
                             required=False)


    args_parser.add_argument('-p', '--processes_num',
                             metavar='processes-number',
                             type=int,
                             help='number of parallel processes',
                             default=multiprocessing.cpu_count(),
                             required=False)


    args_parser.add_argument('-m', '--mpi',
                             metavar='mpi',
                             type=bool,
                             help='Run using MPI',
                             default=False,
                             required=False)


    args = args_parser.parse_args()

    parse_method = args.method
    print('The parse method: ' + str(parse_method))

    processes_num = args.processes_num
    print('Number of parallel processes: ' + str(processes_num))

    csv_file_path = args.csv_file_path
    print('CSV file path: ' + str(csv_file_path))

    output_folder = args.output_folder
    print('Output folder: ' + str(output_folder))

    mpi = args.mpi
    print('MPI: ' + str(mpi))


    tokenized = args.tokenized
    print('Tokenized: ' + str(tokenized))
    

    libclang_path = args.libclang

    use_compression = args.use_compression
    
    print('Use compression: ' + str(use_compression))

    if parse_method == 'AST':
        split_terminals = args.split_terminals
        print(f'Split terminal nodes: {split_terminals}')
        ast_parser = AstParser(libclang_path, csv_file_path, output_folder, use_compression, processes_num, split_terminals, tokenized, mpi)
        if mpi:
            ast_parser.parse_mpi()
        else:
            ast_parser.parse_csv()
    elif parse_method == 'code':
        input_folder = args.input_folder
        print('Input folder: ' + str(input_folder))
        ast_to_code_parser = AstToCodeParser(output_folder, csv_file_path, use_compression, processes_num, tokenized)
        ast_to_code_parser.parse_asts_to_code(input_folder)
    elif parse_method == 'roundtrip':
        input_folder = args.input_folder
        split_terminals = args.split_terminals

        if mpi:
            from cpp_ast_parser.roundtrip import roundtrip_mpi
            roundtrip_mpi(input_folder, output_folder, csv_file_path, libclang_path, use_compression, split_terminals, tokenized)

        else:
            print('Not implemented yet, only with MPI support.')

    else:
        print('Please choose a valid method: AST, code or round trip')



if __name__ == "__main__":
   main()



