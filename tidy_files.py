import os


def add_readability_braces(file):
    if os.system(f'clang-tidy {file} -fix >/dev/null 2>&1') != 0:
        raise RuntimeError('There are error(s) in the source code file, therefore the file cannot completely be parsed')


def preprocess_file(file):
    includes_usings = []
    new_file_name = '/'.join(file.split('/')[:-1]) + 'preprocessed_' + file.split('/')[-1]
    with open(file) as f, open(new_file_name, "w") as new_f:
        code = f.read()

        for elements in [line.split(';') for line in code.split('\n')]:
            for element in elements:
                if element.startswith('#include'):
                    includes_usings.append(element)
                if element.startswith('using namespace'):
                    includes_usings.append(element + ';')

        if not '#define ONLINE_JUDGE' in code:
            new_f.write('#define ONLINE_JUDGE \n')

        new_f.write(code)

    # remove original file
    os.remove(file)
    # Rename dummy file as the original file
    os.rename(new_file_name, file)

    return includes_usings

def add_includes_usings(file, includes_usings):
    new_file_name = '/'.join(file.split('/')[:-1]) + 'preprocessed_' + file.split('/')[-1]
    with open(file) as f, open(new_file_name, "w") as new_f:
        code = f.read()

        for element in includes_usings:
            new_f.write(f'{element}\n')

        new_f.write('\n')
        new_f.write(code)

    # remove original file
    os.remove(file)
    # Rename dummy file as the original file
    os.rename(new_file_name, file)


