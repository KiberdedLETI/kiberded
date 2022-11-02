#!/bin/bash
datetime_name=`date +"%Y-%m-%d_%H-%M"`
bk_dir='/root/Yandex.Disk/backups/'
main_dir='/root/kiberded/'
main_dir_db='/var/www/html'
dir_db='databases'
dir_keyboards='keyboards'
dir_keyboards_telegram='keyboards_telegram'
dir_messages_telegram='messages_backup'


/bin/tar -czvf $bk_dir/$dir_db/$datetime_name.tar.gz -C $main_dir_db $dir_db
/bin/tar -czvf $bk_dir/$dir_keyboards/$datetime_name.tar.gz -C $main_dir $dir_keyboards
/bin/tar -czvf $bk_dir/$dir_keyboards_telegram/$datetime_name.tar.gz -C $main_dir $dir_keyboards_telegram
/bin/tar -czvf $bk_dir/$dir_messages_telegram/$datetime_name.tar.gz -C $main_dir $dir_messages_telegram

cd /root/kiberded/server
python3.8 daily_backup.py