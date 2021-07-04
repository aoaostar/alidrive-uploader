#!/usr/bin/python3
# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 阿里云盘上传Python3脚本
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha1

from common import LOCK, DATA, print_success, get_running_path, qualify_path, print_error, get_all_file_relative, \
    load_task, print_warn, save_task

if __name__ != '__main__':
    sys.exit()

from AliyunDrive import AliyunDrive


def upload_file(path, filepath):
    drive = AliyunDrive(DATA['DRIVE_ID'], DATA['ROOT_PATH'], DATA['CHUNK_SIZE'])
    # 刷新token
    drive.token_refresh()
    realpath = path + filepath
    drive.load_file(filepath, realpath)
    # 创建目录
    LOCK.acquire()
    try:
        parent_folder_id = drive.get_parent_folder_id(filepath)
    finally:
        LOCK.release()
    # 断点续传
    if DATA['RESUME'] and drive.filepath_hash in DATA['tasks']:
        c_task = DATA['tasks'][drive.filepath_hash]
        if 0 not in (
                c_task['drive_id'],
                c_task['file_id'],
                c_task['upload_id'],
                c_task['part_number'],
                c_task['chunk_size'],
        ):
            drive.drive_id = c_task['drive_id']
            drive.file_id = c_task['file_id']
            drive.upload_id = c_task['upload_id']
            drive.part_number = c_task['part_number']
            drive.chunk_size = c_task['chunk_size']
            # 获取上传地址
            drive.part_upload_url_list = drive.get_upload_url()
            # 上传
            drive.upload()
            # 提交
            if drive.complete():
                return drive.filepath_hash
            return False

    # 创建上传
    create_post_json = drive.create(parent_folder_id)
    if 'rapid_upload' in create_post_json and create_post_json['rapid_upload']:
        print_success('【{filename}】秒传成功！消耗{s}秒'.format(filename=drive.filename, s=time.time() - drive.start_time))
        return drive.filepath_hash
    # 上传
    drive.upload()
    # 提交
    if drive.complete():
        return drive.filepath_hash
    return False


# 配置信息
config = {
    "REFRESH_TOKEN": "refresh_token",
    "DRIVE_ID": "drive_id",
    "ROOT_PATH": "root",
    "FILE_PATH": get_running_path(),
    "MULTITHREADING": False,
    "MAX_WORKERS": 5,
    "CHUNK_SIZE": 104857600,
    "RESUME": False,
    "OVERWRITE": False
}
if not os.path.exists(get_running_path('/config.json')):
    print_error('请配置好config.json后重试')
    with open(get_running_path('/config.json'), 'w') as f:
        f.write(json.dumps(config))
    sys.exit()
try:
    with open(get_running_path('/config.json'), 'rb') as f:

        config.update(json.loads(f.read().decode('utf-8')))
        DATA['REFRESH_TOKEN'] = config.get('REFRESH_TOKEN')
        DATA['FILE_PATH'] = config.get('FILE_PATH')
        DATA['DRIVE_ID'] = config.get('DRIVE_ID')
        DATA['CHUNK_SIZE'] = config.get('CHUNK_SIZE')
        DATA['ROOT_PATH'] = qualify_path(config.get('ROOT_PATH'))
        # 启用多线程
        DATA['MULTITHREADING'] = bool(config.get('MULTITHREADING'))
        # 断点续传
        DATA['RESUME'] = bool(config.get('RESUME'))
        DATA['OVERWRITE'] = bool(config.get('OVERWRITE'))
        # 线程池最大线程数
        DATA['MAX_WORKERS'] = config.get('MAX_WORKERS')
except Exception as e:
    print_error('请配置好config.json后重试')
    raise e
# 命令行参数上传
if len(sys.argv) == 3:
    DATA['ROOT_PATH'] = qualify_path(sys.argv[2])
    abspath = os.path.abspath(sys.argv[1])
    if os.path.isdir(sys.argv[1]):
        # 目录上传
        DATA['FILE_PATH'] = abspath
        file_list = get_all_file_relative(DATA['FILE_PATH'])
    else:
        # 单文件上传
        DATA['FILE_PATH'] = os.path.dirname(abspath)
        file_list = [os.path.basename(abspath)]
    DATA['tasks'] = {}
elif len(sys.argv) == 2:
    abspath = os.path.abspath(sys.argv[1])
    if os.path.isdir(abspath):
        # 目录上传
        DATA['FILE_PATH'] = abspath
        file_list = get_all_file_relative(DATA['FILE_PATH'])
    else:
        # 单文件上传
        DATA['FILE_PATH'] = os.path.dirname(abspath)
        file_list = [os.path.basename(abspath)]
    DATA['tasks'] = {}
else:
    file_list = get_all_file_relative(DATA['FILE_PATH'])
    DATA['tasks'] = load_task()

DATA['FILE_PATH'] = qualify_path(DATA['FILE_PATH'])

task_template = {
    "filepath": None,
    "upload_time": 0,
    "drive_id": 0,
    "file_id": 0,
    "upload_id": 0,
    "part_number": 0,
    "chunk_size": 0,
}
if DATA['MULTITHREADING']:
    with ThreadPoolExecutor(max_workers=DATA['MAX_WORKERS']) as executor:
        future_list = []
        for file in file_list:
            filepath_hash = sha1(file.encode('utf-8')).hexdigest()
            if filepath_hash not in DATA['tasks']:
                DATA['tasks'][filepath_hash] = task_template.copy()
            DATA['tasks'][filepath_hash]['filepath'] = file
            if DATA['tasks'][filepath_hash]['upload_time'] > 0:
                print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
            else:
                if DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                    # 提交线程
                    future = executor.submit(upload_file, DATA['FILE_PATH'], file)
                    future_list.append(future)

        for res in as_completed(future_list):
            if res.result():
                DATA['tasks'][res.result()]['upload_time'] = time.time()
                save_task(DATA['tasks'])
            else:
                print_error(os.path.basename(file) + ' 上传失败')
else:
    for file in file_list:
        filepath_hash = sha1(file.encode('utf-8')).hexdigest()
        if filepath_hash not in DATA['tasks']:
            DATA['tasks'][filepath_hash] = task_template.copy()
        DATA['tasks'][filepath_hash]['filepath'] = file
        if DATA['tasks'][filepath_hash]['upload_time'] > 0:
            print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
        else:
            if DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                if upload_file(DATA['FILE_PATH'], file):
                    DATA['tasks'][filepath_hash]['upload_time'] = time.time()
                    save_task(DATA['tasks'])
                else:
                    print_error(os.path.basename(file) + ' 上传失败')
