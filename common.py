# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 公共函数类
# +-------------------------------------------------------------------
# | Author: Pluto <i@abcyun.cc>
# +-------------------------------------------------------------------

import hashlib
import json
import os
import sys
import threading
import time
from xml.dom.minidom import parseString

from sqlite import sqlite

LOCK = threading.Lock()
DATA = {
    'config': {},
    'folder_id_dict': {},
    'task_template': {
        "filepath": None,
        "filesize": 0,
        "hash": '',
        "status": 0,
        "create_time": time.time(),
        "finish_time": 0,
        "spend_time": 0,
        "drive_id": '0',
        "file_id": '0',
        "upload_id": '0',
        "part_number": 0,
        "chunk_size": 104857600,
    }
}


# 处理路径
def qualify_path(path):
    if not path:
        return ''
    return path.replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep


# 获取运行目录
def get_running_path(path=''):
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable) + path
    elif __file__:
        return os.path.dirname(__file__) + path


def get_config_file_path():
    return get_running_path('/config.json')


def get_db_file_path():
    return get_running_path('/db.db')


# 读取配置项
# @param key 取指定配置项，若不传则取所有配置[可选]
def get_config(key=None):
    # 判断是否从文件读取配置
    if not os.path.exists(get_config_file_path()): return None

    with open(get_config_file_path(), 'rb') as f:
        f_body = f.read().decode('utf-8')
    if not f_body: return None
    config = json.loads(f_body)
    for value in [
        'MULTITHREADING',
        'RESUME',
        'OVERWRITE',
        'RESIDENT',
    ]:
        if value in config:
            DATA['config'][value] = bool(config[value])
    config['ROOT_PATH'] = qualify_path(config.get('ROOT_PATH')).rstrip(os.sep)
    # 取指定配置项
    if key:
        if key in config: return config[key]
        return None
    return config


def set_config(key, value):
    config = get_config()
    # 是否需要初始化配置项
    if not config: config = {}
    # 是否需要设置配置值
    if key:
        config[key] = value
    with open(get_config_file_path(), 'w') as f:
        f.write(json.dumps(config))
        f.flush()
    return True


def get_db():
    return sqlite().dbfile(get_db_file_path())


def get_hash(filepath, block_size=2 * 1024 * 1024):
    with open(filepath, 'rb') as f:
        sha1 = hashlib.sha1()
        while True:
            data = f.read(block_size)
            if not data:
                break
            sha1.update(data)
        return sha1.hexdigest()


def get_all_file(path):
    result = []
    get_dir = os.listdir(path)
    for i in get_dir:
        sub_dir = os.path.join(path, i)
        if os.path.isdir(sub_dir):
            result.extend(get_all_file(sub_dir))
        else:
            result.append(sub_dir)
    return result


def get_all_file_relative(path):
    result = []
    if not os.path.exists(path):
        return result
    get_dir = os.listdir(path)
    for i in get_dir:
        sub_dir = os.path.join(path, i)
        if os.path.isdir(sub_dir):
            all_file = get_all_file_relative(sub_dir)
            all_file = map(lambda x: i + os.sep + x, all_file)
            result.extend(all_file)
        else:
            result.append(i)
    return result


def print_info(message, id=None):
    # i = random.randint(34, 37)
    i = 36
    log(message, id)
    print('\033[7;30;{i}m{message}\033[0m'.format(message=message, i=i))


def print_warn(message, id=None):
    log(message, id)
    print('\033[7;30;33m{message}\033[0m'.format(message=message))


def print_error(message, id=None):
    log(message, id)
    print('\033[7;30;31m{message}\033[0m'.format(message=message))


def print_success(message, id=None):
    log(message, id)
    print('\033[7;30;32m{message}\033[0m'.format(message=message))


def date(timestamp=None):
    if not timestamp:
        timestamp = get_timestamp()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def get_timestamp():
    return int(time.time())


def log(message, id=None):
    if not id is None:
        db = get_db()
        idata = {
            'task_id': id,
            'content': message,
            'create_time': get_timestamp(),
        }
        db.table('task_log').insert(idata)
    file = get_running_path('/log/' + time.strftime("%Y-%m-%d", time.localtime()) + '.log')
    if not os.path.exists(os.path.dirname(file)):
        os.mkdir(os.path.dirname(file))
    with open(file, 'a') as f:
        f.write('【{date}】{message}\n'.format(date=date(time.time()), message=message))


def get_xml_tag_value(xml_string, tag_name):
    DOMTree = parseString(xml_string)
    DOMTree = DOMTree.documentElement
    tag = DOMTree.getElementsByTagName(tag_name)
    if len(tag) > 0:
        for node in tag[0].childNodes:
            if node.nodeType == node.TEXT_NODE:
                return node.data
    return False


def load_task():
    db = get_db()
    return db.table('task').where('finish_time=?', 0).order('create_time asc').limit('25').select()


def save_task(task_id, udata):
    db = get_db()
    return db.table('task').where('id=?', (task_id,)).update(udata)


def create_task(data):
    db = get_db()
    db.table('task').insert(data)


def read_in_chunks(file_object, chunk_size=16 * 1024, total_size=10 * 1024 * 1024):
    load_size = 0
    while True:
        if load_size >= total_size:
            break
        data = file_object.read(chunk_size)
        if not data:
            break
        load_size += 16 * 1024
        yield data
