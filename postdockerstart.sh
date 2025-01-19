ln -s  /usr/src/paperless/scripts/postdockerstart.sh /etc/init.d/postdockerstart.sh
apt update
apt install cron nano procps -y
/usr/src/paperless/scripts/setup_venv.sh
printenv >> /etc/environment
crontab -u root /usr/src/paperless/scripts/cronjob
#cron -f
cron
