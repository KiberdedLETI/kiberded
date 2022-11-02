"""
Скрипт для создания БД из файлов в папке messages_backup
"""

import sqlite3
import os
import pickle
import toml
import sys
import telebot

try:
    config = toml.load('./configuration.toml')  # если импортируется из корня
except FileNotFoundError:
    try:
        config = toml.load('../configuration.toml')  # если импортируется из папки server
    except FileNotFoundError:
        print('configuration.toml не найден!')
        sys.exit()

path = config.get('Kiberded').get('path')

for dir in os.listdir(f'{path}messages_backup'):
    if dir == 'database.db':
        continue
    for file in os.listdir(f'{path}messages_backup/{dir}'):
        with open(f'{path}messages_backup/{dir}/{file}', 'rb') as f:
            backup = pickle.load(f)
        with sqlite3.connect(f'{path}/messages_backup/database.db') as con:
            cur = con.cursor()
            cur.execute(f'CREATE TABLE IF NOT EXISTS backups('
                        f'is_input_callback text,'
                        f'content_type text,'
                        f'id text,'
                        f'message_id text,'
                        f'from_user_id text,'
                        f'from_user_is_bot text,'
                        f'from_user_first_name text,'
                        f'from_user_username text,'
                        f'from_user_last_name text,'
                        f'date text,'
                        f'chat_id text,'
                        f'chat_type text,'
                        f'chat_title text,'
                        f'chat_username text,'
                        f'chat_first_name text,'
                        f'chat_last_name text,'
                        f'sender_chat text,'
                        f'forward_from text,'
                        f'forward_from_chat text,'
                        f'forward_from_message_id text,'
                        f'forward_signature text,'
                        f'forward_sender_name text,'
                        f'forward_date text,'
                        f'is_automatic_forward text,'
                        f'reply_to_message text,'
                        f'via_bot text,'
                        f'edit_date text,'
                        f'has_protected_content text,'
                        f'media_group_id text,'
                        f'author_signature text,'
                        f'text text,'
                        f'entities text,'
                        f'migrate_to_chat_id text,'
                        f'migrate_from_chat_id text,'
                        f'pinned_message text,'
                        f'id_callback text,'
                        f'inline_message_id text,'
                        f'chat_instance text,'
                        f'data text)')
            if type(backup) is telebot.types.Message:
                cur.execute(f'INSERT INTO backups ('
                            f'is_input_callback,'
                            f'content_type,'
                            f'id,'
                            f'message_id,'
                            f'from_user_id,'
                            f'from_user_is_bot,'
                            f'from_user_first_name,'
                            f'from_user_username,'
                            f'from_user_last_name,'
                            f'date,'
                            f'chat_id,'
                            f'chat_type,'
                            f'chat_title,'
                            f'chat_username,'
                            f'chat_first_name,'
                            f'chat_last_name,'
                            f'sender_chat,'
                            f'forward_from,'
                            f'forward_from_chat,'
                            f'forward_from_message_id,'
                            f'forward_signature,'
                            f'forward_sender_name,'
                            f'forward_date,'
                            f'is_automatic_forward,'
                            f'reply_to_message,'
                            f'via_bot,'
                            f'edit_date,'
                            f'has_protected_content,'
                            f'media_group_id,'
                            f'author_signature,'
                            f'text,'
                            f'entities,'
                            f'migrate_to_chat_id,'
                            f'migrate_from_chat_id,'
                            f'pinned_message) VALUES ('
                            f'?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                            f'?, ?, ?, ?, ?, ?, ?)', [
                                'False',
                                str(backup.content_type),
                                str(backup.id),
                                str(backup.message_id),
                                str(backup.from_user.id),
                                str(backup.from_user.is_bot),
                                str(backup.from_user.first_name),
                                str(backup.from_user.username),
                                str(backup.from_user.last_name),
                                str(backup.date),
                                str(backup.chat.id),
                                str(backup.chat.type),
                                str(backup.chat.title),
                                str(backup.chat.username),
                                str(backup.chat.first_name),
                                str(backup.chat.last_name),
                                str(backup.sender_chat),
                                str(backup.forward_from),
                                str(backup.forward_from_chat),
                                str(backup.forward_from_message_id),
                                str(backup.forward_signature),
                                str(backup.forward_sender_name),
                                str(backup.forward_date),
                                str(backup.is_automatic_forward),
                                str(backup.reply_to_message),
                                str(backup.via_bot),
                                str(backup.edit_date),
                                str(backup.has_protected_content),
                                str(backup.media_group_id),
                                str(backup.author_signature),
                                str(backup.text),
                                str(backup.entities),
                                str(backup.migrate_to_chat_id),
                                str(backup.migrate_from_chat_id),
                                str(backup.pinned_message)
                            ])
            elif type(backup) is telebot.types.CallbackQuery:
                pass
