# Кибердед - ЛЭТИшный Чат-Бот #
![ded working](https://img.shields.io/badge/ded-working-brightgreen) ![python](https://img.shields.io/badge/python-%3E%3D3.8-blue) ![nodejs](https://img.shields.io/badge/nodejs-%3E%3D12.0-blue)

## Участие в разработке ##
- В разделе Issues можно создавать / брать на себя новые задачи и багфиксы. 
При написании руководствуйся предложенными шаблонами и старайся описать проблему подробно.

- Для решения задачи сделай Fork проекта, напиши необходимый код и предложи Pull Request

- При написании Commit'ов рекомендуется придерживаться синтаксиса [Conventional Commits](https://www.conventionalcommits.org/ru/)

## Информация по общей структуре бота ##
#### Основные скрипты

- chat_bot.py - бот ВК

- telegram_bot.py - бот в Телеграм

- main_bot.py - бот-оповещатель с почты (почтовый), todo rename

- scheduler - функционал расписанию (ежедневные алгоритмы, рассылки в ЛС и беседы)


#### Вспомогательные скрипты
- bot_functions/bots_common_funcs.py - все основные функции обоих чат-ботов. 
Общий бэкенд, отличаются лишь возвращаемые id (при наличии) 
- shiza: (успехов разобраться в ней)
  - elements_of_shiza.py - редактор БД во ВКонтакте, запускаемый отдельным потоком.
  - databases_shiza_helper - бОльшая часть функций обработки данных для elements_of_shiza
  - etu_parsing - все, что связано с парсингом данных с сайтов ЛЭТИ
  - daily_functions.py - основные функции для scheduler
- keyboards/create_keyboards.py - здесь создаются все общие для пользователей клавиатуры. 
Настоятельно не рекомендуется писать клавиатуры вручную, в силу проблемного пересоздания в случае чего
- keyboards_telegram/create_keyboards.py - аналогично.

#### todo
-[ ] Дописать документацию здесь и в shiza
-[ ] Перенести отдельно от Readme инструкцию по установке дедов на сервер (ниже)
-[ ] Дописать шаблоны Issues

### Инструкция по установке для админов ###
*todo: *

Дед состоит из пяти поддедов:

| №   | Дед               | Название сервиса |
|-----|-------------------|------------------|
| 1   | Кибердед          | chat_bot         |
| 2   | Кибертележный дед | telegram_bot     |
| 3   | Почтовый дед      | main_bot         |
| 4   | Отслеживающий дед | update_daemon    |
| 5   | Наблюдающий дед   | watcher          |
| 6   | Планировочный дед | scheduler        |
| 7   | Заместитель деда  | proxy            |

### *Заметки* ###
#### Логирование ####
Логирование в журнал осуществляется при помощи библиотеки logging. Вообще в ней есть 5 уровней "важности" логов, но в
журнал попадают только 3 самых жестких:
+ `logger.warning('some_message')`
+ `logger.error('some_message')`
+ `logger.critical('some_message')`

Для просмотра логов есть штука `journalctl`. Основные аргументы - `-u` - выводит логи определенной службы, 
`--since |-S` и `--until | -U` - фильтры по времени

Например: `journalctl -u chat_bot --since today`
## *Установка* ##
Для норм работоспособности необходимы:
+ python 3.8 и выше
+ nodejs 12.0 и выше

Кратенько об установке на чистый сервак
Все команды надо выполнять от рута, если вход в терминал под другим логином - выполняем `sudo su`

1. Лучше использовать Ubuntu 18.04+, потому что на 16.04 ты задолбаешься ставить некоторые пакеты.
2. Если не работает команда `add-apt-repository`, необходимо установить пакет: `apt-get install software-properties-common`
3. В Ubuntu 20.04 стандартная версия python-а - 3.8, необходима не менее 3.8. Для установки:
### Данный пункт уже не актуален, т.к. теперь дед спокойно работает на 3.8 ###
    + Добавить [данный репозиторий](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) в список репозиториев: `add-apt-repository ppa:deadsnakes/ppa`
    + обновить списки пакетов: `apt-get update`
    + установить пакеты: `apt-get install python3.10 python3.10-dev python3.10-distutils python3.10-full`
    + ссылка на python3: `ln /usr/bin/python3.10 /usr/bin/python3`
    + проверить версию: `python3 -V`. Если 3.10+, то все ок, если нет - предыдущий шаг делаем через `update-alternatives `
    + ставим pip: `wget https://bootstrap.pypa.io/get-pip.py` ; `python3 get-pip.py`
5. Для обновляющего деда необходим nodejs и библиотеки express, vk_io и node-telegram-bot-api
   + Ставим nodejs и npm: `apt-get install nodejs npm`
   + обновляем nodejs до последней версии: `npm install -g n` ; `n stable`
   + ставим пакеты: `npm i express` и т.д.
6. Копируем этот репозиторий на сервер:
   + Создаем ssh-ключ: `ssh-keygen`, нажимаем на `Enter` до упора
     + публичный ключ: `cat .ssh/id_rsa.pub` , вывод копируем (начинается с `ssh-rsa`, заканчивается юзером)
     + открываем [страничку](https://github.com/settings/keys) на гитхабе (**Profile - Settings - Keys**)
     + нажимаем **New SSH Key**, в поле **Title** вводим что-нибудь, в поле **Key** вставляем публичный ключ, тыкаем **Add SSH Key**
   + На всякий случай, выполняем `apt-get install git`
   + Копируем репозиторий: `git clone git@github.com:evgensetrov/email-py.git`
7. Установка утилиты *ded*:
   + `cd email-py`
   + `ln --force server/ded /usr/bin/ded`
   + `chmod a+x server/ded`
   + Проверка работоспособности: `ded status` должен выдать что-то типа того, что все деды не работают
8. Установка необходимых пакетов:
   + `python3 -m pip install -r requirements.txt`
   + `apt-get install libsystemd-dev`
   + ***install python-systemd!!!***
   + `cd update`
   + `npm install express`
   + `npm install vk-io`
9. npm жрет много места, его теперь можно убрать:
   + `apt-get remove npm`
10. Для работы дедов нужен конфиг-файл `configuration.toml` в корне директории, его нужно создать по примеру 
`configuration_example.toml`
11. Установка служб (дедов) в systemd:
    + `cd ../server/services`
    + `bash install.sh`
    + Устанавливаем по очереди все 5 служб
12. Прочие ништяки:
    + Резервное копирование:
      + Установка yandex-disk: `echo "deb http://repo.yandex.ru/yandex-disk/deb/ stable main" | sudo tee -a /etc/apt/sources.list.d/yandex-disk.list > /dev/null && wget http://repo.yandex.ru/yandex-disk/YANDEX-DISK-KEY.GPG -O- | sudo apt-key add - && sudo apt-get update && sudo apt-get install -y yandex-disk`
      + начальная настройка и вход в аккаунт: `yandex-disk setup`, по ссылке надо ввести код в браузере с войденным аккаунтом деда
      + несинхронизируемые папки можно добавить в `~/.config/yandex-disk/config.cfg` через exclude-dirs, например: `exclude-dirs=kiberded`
      + напуск демона: `yandex-disk start`
      + бекап каждый день в 00:01: `crontab -e`, добавляем `1 0 * * * sh /root/email-py/server/daily-backup.sh` (только если юзер root, см. полный путь до email-py)
    + Перезагрузка:
      + ~деда каждую ночь: `crontab -e`, добавляем `0 0 * * * ded restart --all`
      + ~ сервера каждую неделю по воскресеньям: `crontab -e`, добавляем `0 0 * * 0 reboot`
    + Приветствие в виде ascii-сан-саныча при подключении по ssh
    + Максимальный объем журнала: `journalctl --vacuum-size=500M`
