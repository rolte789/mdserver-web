# coding:utf-8

import sys
import io
import os
import time
import re
import json

sys.path.append(os.getcwd() + "/class/core")
import mw
import site_api

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'pgadmin'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def getConf():
    return mw.getServerDir() + '/web_conf/nginx/vhost/pgadmin.conf'


def getConfInc():
    return getServerDir() + "/" + getCfg()['path'] + '/config.inc.php'


def getPort():
    file = getConf()
    content = mw.readFile(file)
    rep = 'listen\s*(.*);'
    tmp = re.search(rep, content)
    return tmp.groups()[0].strip()


def getHomePage():
    try:
        port = getPort()
        ip = '127.0.0.1'
        if not mw.isAppleSystem():
            ip = mw.getLocalIp()

        cfg = getCfg()
        auth = cfg['username']+':'+cfg['password']
        rand_path = cfg['path']
        url = 'http://' + auth + '@' + ip + ':' + port + '/' + rand_path + '/index.php'
        return mw.returnJson(True, 'OK', url)
    except Exception as e:
        return mw.returnJson(False, '插件未启动!')



def contentReplace(content):
    service_path = mw.getServerDir()
    tmp = mw.execShell(
        'cat /dev/urandom | head -n 32 | md5sum | head -c 16')
    blowfish_secret = tmp[0].strip()
    # print php_ver
    php_conf_dir = mw.getServerDir() + '/web_conf/php/conf'
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$BLOWFISH_SECRET}', blowfish_secret)

    port = cfg["port"]
    rep = 'listen\s*(.*);'
    content = re.sub(rep, "listen " + port + ';', content)
    return content


def initCfg():
    cfg = getServerDir() + "/cfg.json"
    if not os.path.exists(cfg):
        data = {}
        data['port'] = '5051'
        data['choose'] = 'mysql'
        data['path'] = ''
        data['username'] = 'admin'
        data['password'] = 'admin'
        mw.writeFile(cfg, json.dumps(data))


def setCfg(key, val):
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    data = json.loads(data)
    data[key] = val
    mw.writeFile(cfg, json.dumps(data))


def getCfg():
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    data = json.loads(data)
    return data


def returnCfg():
    cfg = getServerDir() + "/cfg.json"
    data = mw.readFile(cfg)
    return data


def __release_port(port):
    from collections import namedtuple
    try:
        import firewall_api
        firewall_api.firewall_api().addAcceptPortArgs(port, 'pgAdmin默认端口', 'port')
        return port
    except Exception as e:
        return "Release failed {}".format(e)


def __delete_port(port):
    from collections import namedtuple
    try:
        import firewall_api
        firewall_api.firewall_api().delAcceptPortArgs(port, 'tcp')
        return port
    except Exception as e:
        return "Release failed {}".format(e)


def openPort():
    conf = getCfg()
    port = conf['port']
    for i in [port]:
        __release_port(i)
    return True


def delPort():
    conf = getCfg()
    port = conf['port']
    for i in [port]:
        __delete_port(i)
    return True


def cleanNginxLog():
    log_a = accessLog()
    log_e = errorLog()

    for i in [log_a, log_e]:
        if os.path.exists(i):
            cmd = "echo '' > " + i
            mw.execShell(cmd)


def initReplace():

    pma_dir = getServerDir() + "/pgadmin"
    if os.path.exists(pma_dir):
        rand_str = mw.getRandomString(6)
        rand_str = rand_str.lower()
        pma_dir_dst = pma_dir + "_" + rand_str
        mw.execShell("mv " + pma_dir + " " + pma_dir_dst)
        setCfg('path', 'pgadmin_' + rand_str)

    file_tpl = getPluginDir() + '/conf/pgadmin.conf'
    file_run = getConf()
    if not os.path.exists(file_run):
        centent = mw.readFile(file_tpl)
        centent = contentReplace(centent)
        mw.writeFile(file_run, centent)

    pma_path = getServerDir() + '/pma.pass'
    if not os.path.exists(pma_path):
        username = mw.getRandomString(8)
        password = mw.getRandomString(10)
        pass_cmd = username + ':' + mw.hasPwd(password)
        setCfg('username', username)
        setCfg('password', password)
        mw.writeFile(pma_path, pass_cmd)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/pgadmin.service'

    if os.path.exists(systemDir) and not os.path.exists(systemService):
        systemServiceTpl = getPluginDir() + '/init.d/pgadmin.service.tpl'
        service_path = mw.getServerDir()
        content = mw.readFile(systemServiceTpl)
        content = content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, content)
        mw.execShell('systemctl daemon-reload')


def pgOp(method):
    file = initReplace()

    current_os = mw.getOs()
    if current_os == "darwin":
        return 'ok'

    if current_os.startswith("freebsd"):
        data = mw.execShell('service' + getPluginName() + ' ' + method)
        if data[1] == '':
            return 'ok'
        return data[1]

    data = mw.execShell('systemctl ' + method+ ' ' + getPluginName())
    if data[1] == '':
        return 'ok'
    return data[1]

def status():
    sock = '/tmp/pgadmin4.sock'
    if os.path.exists(sock):
        return 'start'
    return 'stop'


def start():
    initCfg()
    openPort()

    pgOp('start')

    cleanNginxLog()
    return 'ok'


def stop():
    pgOp('stop')
    delPort()
    mw.restartWeb()
    return 'ok'


def restart():
    return pgOp('restart')


def reload():
    return pgOp('reload')

def getPmaOption():
    data = getCfg()
    return mw.returnJson(True, 'ok', data)


def getPmaPort():
    try:
        port = getPort()
        return mw.returnJson(True, 'OK', port)
    except Exception as e:
        # print(e)
        return mw.returnJson(False, '插件未启动!')


def setPmaPort():
    args = getArgs()
    data = checkArgs(args, ['port'])
    if not data[0]:
        return data[1]

    port = args['port']
    if port == '80':
        return mw.returnJson(False, '80端不能使用!')

    file = getConf()
    if not os.path.exists(file):
        return mw.returnJson(False, '插件未启动!')
    content = mw.readFile(file)
    rep = r'listen\s*(.*);'
    content = re.sub(rep, "listen " + port + ';', content)
    mw.writeFile(file, content)

    setCfg("port", port)
    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaChoose():
    args = getArgs()
    data = checkArgs(args, ['choose'])
    if not data[0]:
        return data[1]

    choose = args['choose']
    setCfg('choose', choose)

    pma_path = getCfg()['path']
    conf_run = getServerDir() + "/" + pma_path + '/config.inc.php'

    conf_tpl = getPluginDir() + '/conf/config.inc.php'
    content = mw.readFile(conf_tpl)
    content = contentReplace(content)
    mw.writeFile(conf_run, content)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaUsername():
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]

    username = args['username']
    setCfg('username', username)

    cfg = getCfg()
    pma_path = getServerDir() + '/pma.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaPassword():
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    password = args['password']
    setCfg('password', password)

    cfg = getCfg()
    pma_path = getServerDir() + '/pma.pass'
    username = mw.getRandomString(10)
    pass_cmd = cfg['username'] + ':' + mw.hasPwd(cfg['password'])
    mw.writeFile(pma_path, pass_cmd)

    mw.restartWeb()
    return mw.returnJson(True, '修改成功!')


def setPmaPath():
    args = getArgs()
    data = checkArgs(args, ['path'])
    if not data[0]:
        return data[1]

    path = args['path']

    if len(path) < 5:
        return mw.returnJson(False, '不能小于5位!')

    old_path = getServerDir() + "/" + getCfg()['path']
    new_path = getServerDir() + "/" + path

    mw.execShell("mv " + old_path + " " + new_path)
    setCfg('path', path)
    return mw.returnJson(True, '修改成功!')


def accessLog():
    return getServerDir() + '/access.log'


def errorLog():
    return getServerDir() + '/error.log'


def installVersion():
    return mw.readFile(getServerDir() + '/version.pl')

def pluginsDbSupport():
    data = {}

    data['installed'] = 'no'
    install_path = getServerDir()
    if not os.path.exists(install_path):
        return mw.returnJson(True, 'ok', data) 

    data['installed'] = 'ok'
    data['status'] = status()
    if (data['status'] == 'stop'):
        return mw.returnJson(True, 'ok', data)

    data['cfg'] = getCfg()
    port = getPort()
    ip = '127.0.0.1'
    if not mw.isAppleSystem():
        ip = mw.getLocalIp()

    cfg = data['cfg']
    auth = cfg['username']+':'+cfg['password']
    rand_path = cfg['path']
    home_page = 'http://' + auth + '@' + ip + ':' + port + '/' + rand_path + '/index.php'

    data['home_page'] = home_page
    data['version'] = installVersion().strip()

    return mw.returnJson(True, 'ok', data)

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'conf':
        print(getConf())
    elif func == 'version':
        print(installVersion())
    elif func == 'get_cfg':
        print(returnCfg())
    elif func == 'config_inc':
        print(getConfInc())
    elif func == 'get_home_page':
        print(getHomePage())
    elif func == 'get_pma_port':
        print(getPmaPort())
    elif func == 'set_pma_port':
        print(setPmaPort())
    elif func == 'get_pma_option':
        print(getPmaOption())
    elif func == 'set_pma_choose':
        print(setPmaChoose())
    elif func == 'set_pma_username':
        print(setPmaUsername())
    elif func == 'set_pma_password':
        print(setPmaPassword())
    elif func == 'set_pma_path':
        print(setPmaPath())
    elif func == 'access_log':
        print(accessLog())
    elif func == 'error_log':
        print(errorLog())
    elif func == 'plugins_db_support':
        print(pluginsDbSupport())
    else:
        print('error')
