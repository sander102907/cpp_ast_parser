import argparse
from AST_parser import AstParser
from AST_to_code import AstToCodeParser


def main():
    args_parser = argparse.ArgumentParser(
        description='AST parser can create ASTs from CPP code in JSON format and can transform the AST trees back to code')

    args_parser.add_argument('method',
                             metavar='method',
                             type=str,
                             help='The parse method: AST or code',
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


    args_parser.add_argument('-l', '--libclang',
                             metavar='libclang-path',
                             type=str,
                             help='path to clang library libclang.so file',
                             required=False)


    args = args_parser.parse_args()

    parse_method = args.method
    print('The parse method: ' + str(parse_method))

    csv_file_path = args.csv_file_path
    print('CSV file path: ' + str(csv_file_path))

    output_folder = args.output_folder
    print('Output folder: ' + str(output_folder))

    input_folder = args.input_folder
    print('Input folder: ' + str(input_folder))

    libclang_path = args.libclang

    if parse_method == 'AST':
        ast_parser = AstParser(libclang_path, csv_file_path, output_folder)
        ast_parser.parse_csv()
    elif parse_method == 'code':
        ast_to_code_parser = AstToCodeParser(input_folder, output_folder, csv_file_path)
        ast_to_code_parser.parse_asts_to_code()
    else:
        print('Please choose a valid method: AST or code')



if __name__ == "__main__":
   main()