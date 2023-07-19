# dependencies: [update_daemon]
"""
Небольшой файлик с зависимостями, какой скрипт за каких дедов отвечает.

Костыльно, но зато очень удобно при коммитах: перезагружаются не все сервисы, а только те, которые (или зависимости
которых) были отредактированы
"""

import os


mail_bot = 'mail_bot'

chat_bot = 'chat_bot'

scheduler = 'scheduler'

telegram_bot = 'telegram_bot'

update_daemon = 'update_daemon'

watcher = 'watcher'

with open('../.gitignore') as f:
    gitignore_data = f.readlines()


def recursion_scan(path, files_arr=[]):
    with os.scandir(path) as files:
        for file in files:
            if file.path[14:] + '\n' in gitignore_data:
                continue
            if os.path.isfile(file.path):
                if file.path.endswith(('.db', '.pyc',)):
                    continue
                files_arr.append(file.path)
            else:
                if file.name.startswith('.'):
                    continue
                recursion_scan(file.path)
    return files_arr


def get_file_dependencies(file_path):
    if file_path.endswith(('.png', '.txt', '.md',)):
        dependencies = []
    else:
        with open(file_path, encoding='utf-8') as f:
            dependencies = 'None'
            for i in range(3):  # проверяем первые 3 строчки:
                line = f.readline()
                if line.startswith('# dependencies'):
                    dependencies = line[17:-2].split(', ')
                    break
    split = file_path.split("/")
    if dependencies == 'None':
        if split[-1].endswith('__init__.py'):
            dependencies = []
        else:
            try:
                path_init = '/root/kiberded/' + split[3] + '/__init__.py'
                with open(path_init, encoding='utf-8') as f2:
                    for i in range(3):  # проверяем первые 3 строчки:
                        line = f2.readline()
                        if line.startswith('# dependencies'):
                            dep_line = line[17:-2]
                            splitted_dep = dep_line.split(', ')
                            dependencies = []
                            for dep in splitted_dep:
                                dependencies.append(dep)
                            break
            except Exception as e:
                raise ValueError(f'Не найдены зависимости в файле')
    return dependencies


def main():
    all_files = {}
    path = '/root/kiberded'
    files = recursion_scan(path)
    for file in files:
        try:
            dependencies = get_file_dependencies(file)
            all_files[file[15:]] = dependencies
        except FileNotFoundError:
            raise FileNotFoundError(f'Не найден файл {file}')
        except UnicodeDecodeError:
            pass
        except Exception as e:
            raise ValueError(f'Произошла ошибка {str(e)} в файле {file}')
    return all_files
