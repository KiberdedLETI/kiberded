#!/bin/bash
# dependencies: []

cd /root/kiberded
git reset --hard
git fetch
git merge

ln --force /root/kiberded/server/ded /usr/bin/ded
chmod a+x /root/kiberded/server/ded
