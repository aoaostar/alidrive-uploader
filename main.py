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

from common import print_warn, print_error, get_all_file_relative, print_info, print_success

if __name__ != '__main__':
    exit()

from AliyunDrive import AliyunDrive


def get_parent_folder_id(root_path, filepath):
    print_info('检索目录中')
    filepath_split = (root_path + filepath.lstrip(os.sep)).split(os.sep)
    del filepath_split[len(filepath_split) - 1]
    path_name = os.sep.join(filepath_split)
    if not path_name in drive.folder_id_dict:
        parent_folder_id = 'root'
        parent_folder_name = os.sep
        if len(filepath_split) > 0:
            for folder in filepath_split:
                if folder == '':
                    continue
                parent_folder_id = drive.create_folder(folder, parent_folder_id)
                parent_folder_name = parent_folder_name.rstrip(os.sep) + os.sep + folder
                drive.folder_id_dict[parent_folder_name] = parent_folder_id
    else:
        parent_folder_id = drive.folder_id_dict[path_name]
        print_info('已存在目录，无需创建')

    print_info('目录id获取成功{parent_folder_id}'.format(parent_folder_id=parent_folder_id))
    return parent_folder_id


def upload_file(path, filepath):
    realpath = path + filepath
    drive.load_file(filepath, realpath)

    # 创建目录
    parent_folder_id = get_parent_folder_id(ROOT_PATH, filepath)
    # 创建上传
    create_post_json = drive.create(parent_folder_id)
    if 'rapid_upload' in create_post_json and create_post_json['rapid_upload']:
        print_success('【{filename}】秒传成功！消耗{s}秒'.format(filename=drive.filename, s=time.time() - drive.start_time))
        return True

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


# 配置信息
try:
    with open(os.getcwd() + '/config.json', 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
        REFRESH_TOKEN = config.get('REFRESH_TOKEN')
        FILE_PATH = config.get('FILE_PATH')
        DRIVE_ID = config.get('DRIVE_ID')
        ROOT_PATH = config.get('ROOT_PATH').replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep
        # 启用多线程
        MULTITHREADING = bool(config.get('MULTITHREADING'))
        # 线程池最大线程数
        MAX_WORKERS = config.get('MAX_WORKERS')
except Exception as e:
    print_error('请配置好config.json后重试')
    raise e
drive = AliyunDrive(DRIVE_ID, ROOT_PATH, REFRESH_TOKEN)
# 刷新token
drive.token_refresh()
# 命令行参数上传
if len(sys.argv) == 2:
    if os.path.isdir(sys.argv[1]):
        # 目录上传
        FILE_PATH = sys.argv[1]
        file_list = get_all_file_relative(FILE_PATH)
    else:
        # 单文件上传
        FILE_PATH = os.path.dirname(sys.argv[1])
        file_list = [os.path.basename(sys.argv[1])]
    task = {}
else:
    file_list = get_all_file_relative(FILE_PATH)
    task = load_task()

FILE_PATH = FILE_PATH.replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep

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
                    future = executor.submit(upload_file, FILE_PATH, file)
                    future_list.append(future)
            else:
                print_warn(os.path.basename(file) + ' 已上传，无需重复上传')

        for res in as_completed(future_list):
            if res.result():
                task[hexdigest]['upload_time'] = time.time()
                save_task(task)
            else:
                print_error(os.path.basename(file) + ' 上传失败')
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
                if upload_file(FILE_PATH, file):
                    task[hexdigest]['upload_time'] = time.time()
                    save_task(task)
                else:
                    print_error(os.path.basename(file) + ' 上传失败')
        else:
            print_warn(os.path.basename(file) + ' 已上传，无需重复上传')
