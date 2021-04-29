# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 公共函数类
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import hashlib
import os
import random
import time


def get_hash(filepath, block_size=64 * 1024):
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


def print_info(message):
    i = random.randint(34, 37)
    log(message)
    print('\033[7;30;{i}m{message}\033[0m'.format(message=message, i=i))


def print_warn(message):
    log(message)
    print('\033[7;30;33m{message}\033[0m'.format(message=message))


def print_error(message):
    log(message)
    print('\033[7;30;31m{message}\033[0m'.format(message=message))


def print_success(message):
    log(message)
    print('\033[7;30;32m{message}\033[0m'.format(message=message))


def date(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def log(message):
    file = os.getcwd() + '/log/' + time.strftime("%Y-%m-%d", time.localtime()) + '.log'
    if not os.path.exists(os.path.dirname(file)):
        os.mkdir(os.path.dirname(file))
    with open(file, 'a') as f:
        f.write('【{date}】{message}\n'.format(date=date(time.time()), message=message))