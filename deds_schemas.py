# dependencies: [update_daemon]
"""
Небольшой файлик с зависимостями, какой скрипт за каких дедов отвечает.

Костыльно, но зато очень удобно при коммитах: перезагружаются не все сервисы, а только те, которые (или зависимости
которых) были отредактированы
"""

import os


main_bot = 'main_bot'

chat_bot = 'chat_bot'

scheduler = 'scheduler'

telegram_bot = 'telegram_bot'

update_daemon = 'update_daemon'

watcher = 'watcher'

with open('.gitignore') as f:
    gitignore_data = f.readlines()


def recursion_scan(path, files_arr=[]):
    with os.scandir(path) as files:
        for file in files:
            if file.path[1:] + '\n' in gitignore_data:
                continue
            if os.path.isfile(file.path):
                if file.path.endswith('.db') or \
                        file.path.endswith('.pyc'):
                    continue
                files_arr.append(file.path)
            else:
                if file.name.startswith('.'):
                    continue
                recursion_scan(file.path)
    return files_arr


def main():
    all_files = {}
    path = './'
    files = recursion_scan(path)
    for file in files:
        if file.endswith('.png') or \
                file.endswith('.txt') or \
                file.endswith('.md'):
            dependencies = []
        else:
            with open(file, encoding='utf-8') as f:
                dependencies = 'None'
                for i in range(3):  # проверяем первые 3 строчки:
                    line = f.readline()
                    if line.startswith('# dependencies'):
                        exec(f'dependencies = {line[16:]}')
                        break
        split = file.split("\\")
        if dependencies == 'None':
            if split[-1].endswith('__init__.py'):
                dependencies = []
            else:
                try:
                    with open(split[0] + '\\__init__.py', encoding='utf-8') as f2:
                        for i in range(3):  # проверяем первые 3 строчки:
                            line = f2.readline()
                            if line.startswith('# dependencies'):
                                exec(f'dependencies = {line[16:]}')
                                break
                except:
                    dependencies = 'None'
        if dependencies == 'None':
            raise ValueError(f'Не обнаружены необходимые зависимости в файле {file}')
        all_files[file] = dependencies
    print(all_files)


if __name__ == '__main__':
    print(main())
