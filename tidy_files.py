import os


def tidy_file(file):
    if os.system(f'clang-tidy {file} -fix -checks="readability-braces-around-statements" >/dev/null 2>&1') != 0:
        print(f'failed on {file}')
