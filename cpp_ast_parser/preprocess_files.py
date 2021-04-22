from tqdm import tqdm
import queue as queue
import json
import os
import pandas as pd
import re


def preprocess_csv(input_file, output_file):
    header = True
    df = pd.read_csv(input_file, chunksize=5e5)

    for chunk in df:
        chunk = chunk[chunk['programmingLangauge'].str.contains('C\+\+')]
        chunk = chunk[~chunk['solution'].isnull()]
        tqdm.pandas()
        chunk[['solution','imports']] = chunk.progress_apply(preprocess_solution, axis=1, result_type='expand')
        chunk.to_csv(output_file, header=header, index=False, mode='a')
        header = False


def preprocess_solution(row):
    solution = row['solution']
    includes_usings = []
    include_regex = re.compile(r'^#*.include')
    using_regex = re.compile(r'^using')
    lines = re.split(';|\n', solution)
    includes_usings += list(filter(include_regex.search, lines))
    includes_usings += [element + ';' for element in list(filter(using_regex.search, lines))]

    if not '#define ONLINE_JUDGE' in solution:
        solution = '#define ONLINE_JUDGE \n' + solution

    return solution, includes_usings


if __name__ == '__main__':
    input_file = '../codeforces-scraper/data/contests_solutions/solutions_600.csv'
    output_file = '../data/cpp_preprocessed/solutions_600.csv'

    preprocess_csv(input_file, output_file)
