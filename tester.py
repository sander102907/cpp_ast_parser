import pexpect
from tqdm import tqdm
import pandas as pd
import re
import os
import threading
import multiprocessing
import queue as queue
import subprocess
from threading import Timer
import time


def test_programs(input_folder, compile_folder, test_results_path):
    # Work with threads to increase the speed
    max_task = multiprocessing.cpu_count()

    solutions = pd.read_csv('../codeforces-scraper/data/contests_solutions_metadata/solutions_600.csv')
    problems = pd.read_csv('../codeforces-scraper/data/contests_problems/problems_data_600.csv')

    os.makedirs(compile_folder, exist_ok=True)

    return_data = multiprocessing.Queue()

    info_df = pd.DataFrame(columns=['program', 'compiled', 'amt_tests_failed', 'amt_tests_passed'])

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
                                args=(file_queue, pbar, solutions, problems, compile_folder, return_data))
            t.daemon = True
            t.start()

        # Fill the queue with files.
        for f in file_paths:
            file_queue.put(f)

        # Wait for all threads to be done.
        file_queue.join()

        
        while not return_data.empty():
            info_df = info_df.append(return_data.get(), ignore_index=True)
        info_df.to_csv(test_results_path, index=False)

    except KeyboardInterrupt:
        os.kill(0, 9)            


def program_tester(file_queue, pbar, solutions, problems, compile_folder, return_data):
    while True:
        file_path = file_queue.get()  
        passed_tests = 0
        failed_tests = 0 
        compiled = True 

        try:
            solution = int(file_path.split('/')[-1].split('.')[0])
        except ValueError:
            file_queue.task_done()
            pbar.update()
            continue

        compiled_file_path = f'{compile_folder}{solution}.out'
        if not os.path.isfile(compiled_file_path):
            proc = subprocess.Popen(['g++', file_path, '-o', compiled_file_path, '-std=c++17'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # timeout after 10 seconds
            t = Timer(10, proc.kill)
            t.start()
            proc.wait()

        solution_data = solutions[solutions['solutionId'] == solution]

        tests = problems[(problems['contestId'] == solution_data['contestId'].iloc[0]) & (problems['problem'] == solution_data['problem'].iloc[0])]['allTests'].iloc[0]

        tests_split = re.split(r'([^()]+)', tests[1:-1])
        tests_split_filtered = list(filter(lambda a: a != '(' and a != ')' and a != ', ', tests_split))

        try:
            start = time.time() 
            for test in tests_split_filtered:
                if time.time() - start > 10:
                    break
                program_input = test.replace('\\n', '\r\n').replace("'", '').split(', ')[0].strip()
                program_output = test.replace('\\n', '\r\n').replace("'", '').split(', ')[1].strip()

                # Scrip scraped tests that were cut off by codeforces (too long)
                if not program_input.endswith('...'):
                    analyzer = pexpect.spawn(compiled_file_path, encoding='utf-8')
                    analyzer.expect('')
                    analyzer.sendline(program_input)
                    try:
                        analyzer.expect(program_output)
                    except Exception:
                        failed_tests += 1

                passed_tests += 1
                # print(f'test {compiled_file_path}')

        except Exception:
            compiled = False

        pbar.update()
        data = {'program': file_path, 'compiled': compiled, 'amt_tests_failed': failed_tests, 'amt_tests_passed': passed_tests}
        return_data.put(data)
        file_queue.task_done()
    

if __name__ == '__main__':
    input_folder = '../data/ast_trees_to_code/'
    compile_folder = '../data/ast_trees_to_code_compiled/'
    test_results_path = 'test_results4.csv'

    test_programs(input_folder, compile_folder, test_results_path)
