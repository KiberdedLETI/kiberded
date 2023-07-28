#!/bin/bash
# dependencies: []

datetime_name=`date +"%Y-%m-%d_%H-%M"`
bk_dir='/root/backups'
main_dir='/root/kiberded/'
main_dir_db='/root/'
dir_db='databases'
dir_keyboards='keyboards'
dir_keyboards_telegram='keyboards_telegram'
dir_messages_telegram='messages_backup'


/bin/tar -czvf $bk_dir/$dir_db/$datetime_name.tar.gz -C $main_dir_db $dir_db
/bin/tar -czvf $bk_dir/$dir_keyboards/$datetime_name.tar.gz -C $main_dir $dir_keyboards
/bin/tar -czvf $bk_dir/$dir_keyboards_telegram/$datetime_name.tar.gz -C $main_dir $dir_keyboards_telegram
/bin/tar -czvf $bk_dir/$dir_messages_telegram/$datetime_name.tar.gz -C $main_dir $dir_messages_telegram

find $bk_dir/$dir_db -type f -mtime +30 -delete
find $bk_dir/$dir_keyboards -type f -mtime +30 -delete
find $bk_dir/$dir_keyboards_telegram -type f -mtime +30 -delete
find $bk_dir/$dir_messages_telegram -type f -mtime +30 -delete

percent="$(df -hl | awk '/^\/dev\/vda2/ { sum+=$5 } END { print sum }')"

cd /root/kiberded/server
python3 /root/kiberded/server/send.py Использованного пространства на сервере: $percent%

python3 daily_backup.py
