#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

curPath=`pwd`
rootPath=$(dirname "$curPath")
rootPath=$(dirname "$rootPath")
serverPath=$(dirname "$rootPath")

# https://dev.mysql.com/downloads/mysql/
# https://downloads.mysql.com/archives/community/


# /www/server/mysql-community/bin/mysqld --basedir=/www/server/mysql-community --datadir=/www/server/mysql-community/data --initialize-insecure --explicit_defaults_for_timestamp


# cd /www/server/mdserver-web/plugins/mysql-community && bash install.sh install 8.0
# cd /www/server/mdserver-web/plugins/mysql-community && bash install.sh uninstall 8.0
# cd /www/server/mdserver-web && python3 /www/server/mdserver-web/plugins/mysql-community/index.py start 5.7
# cd /www/server/mdserver-web && python3 /www/server/mdserver-web/plugins/mysql-community/index.py fix_db_access
# cd /www/server/mdserver-web && source bin/activate && python3 plugins/mysql/index.py do_full_sync  {"db":"xxx","sign":"","begin":1}

action=$1
type=$2

if id mysql &> /dev/null ;then 
    echo "mysql UID is `id -u mysql`"
    echo "mysql Shell is `grep "^mysql:" /etc/passwd |cut -d':' -f7 `"
else
    groupadd mysql
	useradd -g mysql -s /usr/sbin/nologin mysql
fi


if [ "${2}" == "" ];then
	echo '缺少安装脚本...'
	exit 0
fi 

if [ ! -d $curPath/versions/$2 ];then
	echo '缺少安装脚本2...'
	exit 0
fi

if [ "${action}" == "uninstall" ];then
	
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-community/index.py stop ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-community/index.py initd_uninstall ${type}
	cd $curPath

	if [ -f /usr/lib/systemd/system/mysql-community.service ] || [ -f /lib/systemd/system/mysql-community.service ];then
		systemctl stop mysql-community
		systemctl disable mysql-community
		rm -rf /usr/lib/systemd/system/mysql-community.service
		rm -rf /lib/systemd/system/mysql-community.service
		systemctl daemon-reload
	fi
fi


sh -x $curPath/versions/$2/install_generic.sh $1

if [ "${action}" == "install" ];then
	#初始化

	if [ "$?" != "0" ];then
		exit $?
	fi
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-community/index.py start ${type}
	cd ${rootPath} && python3 ${rootPath}/plugins/mysql-community/index.py initd_install ${type}
fi