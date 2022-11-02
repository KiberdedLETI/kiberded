#! /usr/bin/env python
# -*- coding: utf-8 -*-

# наблюдающий дед

import time
import subprocess
import logging

logger = logging.getLogger('watcher')
console_handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


def proxy_ded(enable=True):
    pass

subprocess.Popen(["python3", "/root/kiberded/server/send.py", "Наблюдающий дед", "активирован"], stdout=subprocess.PIPE)
logger.warning('Наблюдающий дед активирован')
count = 0
timer = 5
while True:
    prompt = subprocess.Popen(["ded", "status", "-a"], stdout=subprocess.PIPE).stdout.read().decode('utf-8')
    if prompt == "ok\n":
        count = 0
        pass
    elif prompt == "dead\n" and count < 3:  # флудим в конфу 3 раза раз в пол часа, дальше забиваем
        ded_status = prompt = subprocess.Popen(["ded", "status", "--without-color"], stdout=subprocess.PIPE).stdout.read().decode('utf-8')
        subprocess.Popen(["python3", "/root/kiberded/server/send.py", "Наблюдающий дед:", "какой-то из дедов помер.", ded_status],
                         stdout=subprocess.PIPE)
        logger.error(f'Деды мертвы: {ded_status}')
        count += 1
    elif prompt == "stopped\n" and count == 0:
        count += 1
        ded_status = prompt = subprocess.Popen(["ded", "status"], stdout=subprocess.PIPE).stdout.read().decode('utf-8')
        subprocess.Popen(
            ["python3", "/root/kiberded/server/send.py", "Наблюдающий дед:", "какой-то из дедов остановлен.", ded_status],
            stdout=subprocess.PIPE)
        logger.error(f'Деды остановлены: {ded_status}')
    else:
        logger.critical(f"Дичь какая-то, походу ded status -a сломался. Вывод: {ded_status}")
    time.sleep(timer)
