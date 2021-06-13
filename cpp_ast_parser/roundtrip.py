import os
from mpi4py import MPI
from AST_parser import AstParser
from AST_to_code import AstToCodeParser
from tester import Tester
from tokenizer import Tokenizer
import pandas as pd
import math
from tqdm import tqdm
from utils import assignment_operators, add_includes_usings


def roundtrip_mpi(ast_folder, code_folder, programs_csv_path, libclang_path, use_compression, split_terminals, tokenized):
    compile_folder = os.path.join(code_folder, 'compiled/')

    # Create output directory if it does not exist yet
    os.makedirs(ast_folder, exist_ok=True)
    os.makedirs(code_folder, exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'asts/'), exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'reserved_tokens/'), exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'name_tokens/'), exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'name_builtin_tokens/'), exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'type_tokens/'), exist_ok=True)
    os.makedirs(os.path.join(ast_folder, 'literal_tokens/'), exist_ok=True)
    os.makedirs(code_folder + 'compiled/', exist_ok=True)

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    tokenizers = {
        'RES': Tokenizer(ast_folder + f'reserved_tokens/reserved_tokens_{rank}.json', tokenized),
        'NAME': Tokenizer(ast_folder + f'name_tokens/name_tokens_{rank}.json', tokenized),
        'NAME_BUILTIN': Tokenizer(ast_folder + f'name_builtin_tokens/name_builtin_tokens_{rank}.json', tokenized),
        'TYPE': Tokenizer(ast_folder + f'type_tokens/type_tokens_{rank}.json', tokenized),
        'LITERAL': Tokenizer(ast_folder + f'literal_tokens/literal_tokens_{rank}.json', tokenized)
    }

    ast_parser = AstParser(libclang_path, programs_csv_path, ast_folder, use_compression, 1, split_terminals, tokenized, True)
    ast_to_code_parser = AstToCodeParser(ast_folder, code_folder, programs_csv_path, use_compression, 1, tokenized)
    tester = Tester()

    # Read csv file in chunks (may be very large)
    programs = pd.read_csv(programs_csv_path, chunksize=1e5)

    def get_files():
        files = []

        # Fill the queue with files.
        for program in list(programs_chunk[['solutionId', 'solution', 'imports']].iterrows()):
                files.append((program[1]['solutionId'], program[1]['solution'], program[1]['imports']))

        return files

    # iterate over the chunks
    for programs_chunk in programs:
        if rank == 0:
            files = get_files()
            batch_size = len(files)/size
            for i in range(1, size):
                data = files[math.ceil(batch_size * i): math.ceil(batch_size * (i + 1))]
                comm.send(data, dest=i)
            files = files[:math.ceil(batch_size)]
        else:
            files = comm.recv(source=0)

        for file in tqdm(files, postfix=f'process: {rank}'):
            program_id, code, imports = file
            try:
                # Parse the AST tree for the program
                ast = ast_parser.parse_ast(code, imports, rank)
            except Exception as e:
                print(f'Skipping file due to code to AST failing: {program_id} - {e}')
                continue

            output =  open(f'{code_folder}{program_id}.cpp', 'w')

            try:
                for child in ast.children:
                    output.write(ast_to_code_parser.parse_node(child))
            except Exception as e:
                print(f'Skipping file due to AST to code failing: {program_id} - {e}')
                output.close()
                continue
            
            output.close()

            imports = [ele for ele in imports[1:-1].split("'") if ele != '' and ele != ', ']
            if 'using namespace std;' not in imports:
                imports.append('using namespace std;')

            add_includes_usings(f'{code_folder}{program_id}.cpp', imports)

            compiles = tester.test_program_compiles(f'{code_folder}{program_id}.cpp', compile_folder)
            
            if compiles:
                ast_parser.ast_file_handler.add_ast(ast, program_id)

                for key, tokenizer in tokenizers.items():
                    tokenizer.merge(ast_parser.tokenizers[key])

            for key in tokenizers.keys():      
                ast_parser.tokenizers[key].clear()

        for tokenizer in tokenizers.values():
            tokenizer.save()

        ast_parser.ast_file_handler.save()
        ast_parser.clear_temp_files()

    