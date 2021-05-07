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

import common
from common import print_warn, print_error, get_all_file_relative, print_success

if __name__ != '__main__':
    exit()

from AliyunDrive import AliyunDrive


def upload_file(path, filepath):
    drive = AliyunDrive(DRIVE_ID, ROOT_PATH, REFRESH_TOKEN, CHUNK_SIZE)
    # 刷新token
    drive.token_refresh()
    realpath = path + filepath
    drive.load_file(filepath, realpath)
    # 创建目录
    common.LOCK.acquire()
    try:
        parent_folder_id = drive.get_parent_folder_id(filepath)
    finally:
        common.LOCK.release()
    # 断点续传
    if RESUME and drive.filepath_hash in common.DATA['tasks']:
        c_task = common.DATA['tasks'][drive.filepath_hash]
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
try:
    
    with open(os.getcwd() + '/aliyundrive-uploader/config.json', 'rb') as f:
        config = {
            "REFRESH_TOKEN": "refresh_token",
            "DRIVE_ID": "drive_id",
            "ROOT_PATH": "root",
            "FILE_PATH": os.getcwd(),
            "MULTITHREADING": False,
            "MAX_WORKERS": 5,
            "CHUNK_SIZE": 104857600,
        }
        config.update(json.loads(f.read().decode('utf-8')))
        REFRESH_TOKEN = config.get('REFRESH_TOKEN')
        FILE_PATH = config.get('FILE_PATH')
        DRIVE_ID = config.get('DRIVE_ID')
        CHUNK_SIZE = config.get('CHUNK_SIZE')
        ROOT_PATH = config.get('ROOT_PATH').replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep
        # 启用多线程
        MULTITHREADING = bool(config.get('MULTITHREADING'))
        # 断点续传
        RESUME = bool(config.get('RESUME'))
        # 线程池最大线程数
        MAX_WORKERS = config.get('MAX_WORKERS')
except Exception as e:
    print_error('请配置好config.json后重试')
    raise e
# 命令行参数上传
if len(sys.argv) == 3:
    ROOT_PATH=sys.argv[2].replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep
    if os.path.isdir(sys.argv[1]):
        # 目录上传
        FILE_PATH = sys.argv[1]
        file_list = get_all_file_relative(FILE_PATH)
    else:
        # 单文件上传
        FILE_PATH = os.path.dirname(sys.argv[1])
        file_list = [os.path.basename(sys.argv[1])]
    common.DATA['tasks'] = {}
elif len(sys.argv) == 2:
    if os.path.isdir(sys.argv[1]):
        # 目录上传
        FILE_PATH = sys.argv[1]
        file_list = get_all_file_relative(FILE_PATH)
    else:
        # 单文件上传
        FILE_PATH = os.path.dirname(sys.argv[1])
        file_list = [os.path.basename(sys.argv[1])]
    common.DATA['tasks'] = {}
else:
    file_list = get_all_file_relative(FILE_PATH)
    common.DATA['tasks'] = common.load_task()

FILE_PATH = FILE_PATH.replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep

if MULTITHREADING:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_list = []
        for file in file_list:
            tmp = {
                "filepath": file,
                "upload_time": 0,
                "drive_id": 0,
                "file_id": 0,
                "upload_id": 0,
                "part_number": 0,
                "chunk_size": 0,
            }
            filepath_hash = sha1(file.encode('utf-8')).hexdigest()
            if not filepath_hash in common.DATA['tasks']:
                common.DATA['tasks'][filepath_hash] = tmp

            if common.DATA['tasks'][filepath_hash]['upload_time'] > 0:
                print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
            else:
                if common.DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                    # 提交线程
                    future = executor.submit(upload_file, FILE_PATH, file)
                    future_list.append(future)

        for res in as_completed(future_list):
            if res.result():
                common.DATA['tasks'][res.result()]['upload_time'] = time.time()
                common.save_task(common.DATA['tasks'])
            else:
                print_error(os.path.basename(file) + ' 上传失败')
else:
    for file in file_list:
        tmp = {
            "filepath": file,
            "upload_time": 0,
            "drive_id": 0,
            "file_id": 0,
            "upload_id": 0,
            "part_number": 0,
            "chunk_size": 0,
        }
        filepath_hash = sha1(file.encode('utf-8')).hexdigest()
        if not filepath_hash in common.DATA['tasks']:
            common.DATA['tasks'][filepath_hash] = tmp
        if common.DATA['tasks'][filepath_hash]['upload_time'] > 0:
            print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
        else:
            if common.DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                if upload_file(FILE_PATH, file):
                    common.DATA['tasks'][filepath_hash]['upload_time'] = time.time()
                    common.save_task(common.DATA['tasks'])
                else:
                    print_error(os.path.basename(file) + ' 上传失败')
