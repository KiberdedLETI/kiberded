#!/bin/bash
cd /root/email-py
git reset --hard
git fetch
git merge

ln --force /root/email-py/server/ded /usr/bin/ded
chmod a+x /root/email-py/server/ded

ded restart -a