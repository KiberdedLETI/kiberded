#!/bin/bash
# dependencies: []

# скрипт для установки сервисов

services=("chat_bot" "main_bot" "update_daemon" "watcher" "scheduler" "telegram_bot")
echo "	Установщик служб: выбери службу"
PS3="Введи циферку: "
select service in ${services[*]}
do
hernya="/"
dir_var="$(pwd)${hernya}$(dirname $0)"
echo ${service}
	if [ "${REPLY}" -le "${#services[@]}" ]; then
		ln -f ${dir_var}${hernya}${service}.service /lib/systemd/system/${service}.service
		systemctl daemon-reload
		systemctl enable ${service}
		systemctl restart ${service}
		echo -en "$Служба установлена и запущена.\n"
	else
		echo -en "$Такой службы нет\n"
	fi
	break
done
