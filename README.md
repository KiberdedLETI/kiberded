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

- main_bot.py - бот-оповещатель с почты (почтовый)

- scheduler - функционал расписанию (ежедневные алгоритмы, рассылки в ЛС и беседы)

#### Вспомогательные скрипты
- bot_functions/bots_common_funcs.py - все основные функции обоих чат-ботов. 
Общий бэкенд, отличаются лишь возвращаемые id (при наличии) 
- shiza: (успехов разобраться в ней)
  - elements_of_shiza.py - редактор БД во ВКонтакте, запускаемый отдельным потоком.
  - databases_shiza_helper - бОльшая часть функций обработки данных для elements_of_shiza
  - etu_parsing - все, что связано с парсингом данных с сайтов ЛЭТИ
  - daily_functions.py - основные функции для scheduler
- keyboards/create_keyboards.py и keyboards_telegram/create_keyboards.py - генераторы общих клавиатур в ВК и ТГ 
соответственно.

### Инструкция по установке для админов ###
Дед состоит из семи поддедов:

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
+ Ubuntu 18.04 и выше
+ python 3.8 и выше

Кратенько об установке на чистый сервак
Все команды надо выполнять от рута, если вход в терминал под другим логином - выполняем `sudo su`

1. Если не работает команда `add-apt-repository`, необходимо установить пакет: `apt-get install software-properties-common`

2. Копируем этот репозиторий на сервер:
   + Создаем ssh-ключ: `ssh-keygen`, нажимаем на `Enter` до упора
     + публичный ключ: `cat .ssh/id_rsa.pub` , вывод копируем (начинается с `ssh-rsa`, заканчивается юзером)
     + открываем [страничку](https://github.com/settings/keys) на гитхабе (**Profile - Settings - Keys**)
     + нажимаем **New SSH Key**, в поле **Title** вводим что-нибудь, в поле **Key** вставляем публичный ключ, тыкаем **Add SSH Key**
   + Копируем репозиторий: `git clone git@github.com:KiberdedLETI/kiberded.git`
3. Установка утилиты *ded*:
   + `cd email-py`
   + `ln --force server/ded /usr/bin/ded`
   + `chmod a+x server/ded`
   + Проверка работоспособности: `ded status` должен выдать что-то типа того, что все деды не работают
4. Установка необходимых пакетов:
   + `python3 -m pip install -r requirements.txt`
   + `apt-get install libsystemd-dev`
   + ***install python-systemd!!!***
5. Заполни `configuration_example.toml` и переименуй в `configuration.toml`
6. Установка служб (дедов) в systemd:
   + `cd ../server/services`
   + `bash install.sh`
   + Устанавливаем по очереди все 5 служб
7. Прочие ништяки:
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

8. Обновление сертификата:
   Надо бы потом сделать нормально, а не через такое кол-во костылей, но пока как есть..

   + поменять флаг ``enable_acme_challenge`` в конфиге деда, чтобы монтировалась директория ``/root/kiberded/update/.well-known``

   + вручную закомментировать ``app.add_middleware(HTTPSRedirectMiddleware)`` в ``app.py``

   + остановить сервис через ``ded stop`` или ``systemctl stop update_daemon``

   + поменять порт с ``443`` на ``80`` в ``update_daemon_starter.py`` и закомментировать параметры ``ssl_keyfile`` и ``ssl_certfile``

   + запустить update_daemon (``ded restart``)

   + в новом сеансе: ``certbot certonly`` -> `2` (Place files in webroot directory (webroot)) -> Please enter the domain name: ``domain`` -> Input the webroot for kiberded.ga: `/root/kiberded/update`

   + если все ок, то остановить деда

   + вернуть в app.py и update_daemon_starter все на место

   + ``ded restart``