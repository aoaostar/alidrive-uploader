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

from common import get_all_file, print_warn, print_error

if __name__ != '__main__':
    exit()

from AliyunDrive import AliyunDrive

# 配置信息
try:
    with open(os.getcwd() + '/config.json', 'r') as f:
        config = json.loads(f.read())
        REFRESH_TOKEN = config.get('REFRESH_TOKEN')
        FILE_PATH = config.get('FILE_PATH')
        DRIVE_ID = config.get('DRIVE_ID')
        PARENT_FILE_ID = config.get('PARENT_FILE_ID')
        # 启用多线程
        MULTITHREADING = bool(config.get('MULTITHREADING'))
        # 线程池最大线程数
        MAX_WORKERS = config.get('MAX_WORKERS')
except:
    print_error('请配置好config.json后重试')
    exit()

drive = AliyunDrive(DRIVE_ID, PARENT_FILE_ID, REFRESH_TOKEN)
# 刷新token
drive.token_refresh()


def upload_file(filepath):
    drive.load_file(filepath)
    # 创建上传
    create_post_json = drive.create()
    upload_url = create_post_json['part_info_list'][0]['upload_url']
    file_id = create_post_json['file_id']
    upload_id = create_post_json['upload_id']

    # 上传
    drive.upload(upload_url)
    # 提交
    return drive.complete(file_id, upload_id)


def load_task():
    try:
        with open(os.getcwd() + '/task.json', 'r') as f:
            task = f.read()
            return json.loads(task)
    except:
        return {}


def save_task(task):
    with open(os.getcwd() + '/task.json', 'w') as f:
        f.write(json.dumps(task))
        f.flush()


# 命令行单文件上传
if len(sys.argv) == 2:
    file_list = [sys.argv[1]]
    task = {}
else:
    file_list = get_all_file(FILE_PATH)
    task = load_task()

pool_executor = ThreadPoolExecutor(MAX_WORKERS)

if MULTITHREADING:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_list = []
        for file in file_list:
            tmp = {
                "filepath": file,
                "upload_time": 0
            }
            hexdigest = sha1(file.encode('utf-8')).hexdigest()
            if not hexdigest in task:
                task[hexdigest] = tmp
            if task[hexdigest]['upload_time'] <= 0:
                # 提交线程
                future = executor.submit(upload_file, file)
                future_list.append(future)
            else:
                print_warn(os.path.basename(file) + ' 已上传，无需重复上传')

        for res in as_completed(future_list):
            if res.result():
                task[hexdigest]['upload_time'] = time.time()
                save_task(task)
else:
    for file in file_list:
        tmp = {
            "filepath": file,
            "upload_time": 0
        }
        hexdigest = sha1(file.encode('utf-8')).hexdigest()
        if not hexdigest in task:
            task[hexdigest] = tmp
        if task[hexdigest]['upload_time'] <= 0:
            if upload_file(file):
                task[hexdigest]['upload_time'] = time.time()
                save_task(task)
        else:
            print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
