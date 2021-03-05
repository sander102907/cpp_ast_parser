import pexpect
from tqdm import tqdm
import pandas as pd
import re
import os
import threading
import multiprocessing
import queue as queue
import subprocess


def test_programs(input_folder, output_folder):
    # Work with threads to increase the speed
    max_task = multiprocessing.cpu_count()

    solutions = pd.read_csv('../codeforces-scraper/data/contests_solutions_metadata/solutions_600.csv')
    problems = pd.read_csv('../codeforces-scraper/data/contests_problems/problems_data_600.csv')

    uncompilable_programs = []
    failed_programs = []
    passed_programs = []

    file_paths = []

    for dirs,_,files in os.walk(input_folder):
        for f in files:
            if f.endswith('.cpp'):
                file_paths.append(dirs + f)

    pbar = tqdm(total=len(file_paths))
    file_queue = queue.Queue(max_task)

    try:
        for _ in range(max_task):
            t = threading.Thread(target=program_tester,
                                args=(file_queue, pbar, solutions, problems, output_folder))
            t.daemon = True
            t.start()

        # Fill the queue with files.
        for f in file_paths:
            file_queue.put(f)

        # Wait for all threads to be done.
        file_queue.join()

    except KeyboardInterrupt:
        os.kill(0, 9)            


def program_tester(file_queue, pbar, solutions, problems, output_folder):
    uncompilable_programs = []
    failed_programs = []
    passed_programs = []
    while True:
        file_path = file_queue.get()  
      
        solution = int(file_path.split('/')[-1].split('.')[0])
        compiled_file_path = f'{output_folder}{solution}.out'
        if not os.path.isfile(compiled_file_path):
            proc = subprocess.Popen(['g++', file_path, '-o', compiled_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.wait()

        solution_data = solutions[solutions['solutionId'] == solution]

        tests = problems[(problems['contestId'] == solution_data['contestId'].iloc[0]) & (problems['problem'] == solution_data['problem'].iloc[0])]['allTests'].iloc[0]

        tests_split = re.split(r'([^()]+)', tests[1:-1])
        tests_split_filtered = list(filter(lambda a: a != '(' and a != ')' and a != ', ', tests_split))

        try:
            for test in tests_split_filtered:
                program_input = test.replace('\\n', '\r\n').replace("'", '').split(', ')[0].strip()
                program_output = test.replace('\\n', '\r\n').replace("'", '').split(', ')[1].strip()

                # Scrip scraped tests that were cut off by codeforces (too long)
                if not program_input.endswith('...'):
                    analyzer = pexpect.spawn(compiled_file_path, encoding='utf-8')

                    for inp in program_input.split('\n'):
                        analyzer.expect('')
                        analyzer.sendline(inp)
                    try:
                        analyzer.expect(program_output)
                    except Exception:
                        failed_programs.append(file_path)
                        break

            passed_programs.append(file_path)

        except Exception:
            uncompilable_programs.append(file_path)

        pbar.update()
        file_queue.task_done()


    print(f'uncompilable_programs: {uncompilable_programs}')
    print(f'failed_programs: {failed_programs}') 
    print(f'passed_programs: {passed_programs}')



if __name__ == '__main__':
    input_folder = '../data/subset/cpp/'
    output_folder = '../data/subset/cpp_compiled/'

    test_programs(input_folder, output_folder)