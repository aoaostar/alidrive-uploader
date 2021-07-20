#!/usr/bin/python3
# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | main.py
# +-------------------------------------------------------------------
# | Author: Pluto <i@abcyun.cc>
# +-------------------------------------------------------------------

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait

from Client import Client
from common import DATA, print_error, get_db, get_timestamp, print_info, load_task, create_task

if __name__ != '__main__':
    sys.exit()

client = Client()
# 配置信息初始化
client.init_config()
# 数据库初始化
client.init_database()
# 命令行参数初始化，读取文件列表
client.init_command_line_parameter()
# 输出配置信息
client.print_config_info()
db = get_db()
# 是否常驻运行
if not DATA['config']['RESIDENT']:
    for v in client.tasks:
        tmp = DATA['task_template'].copy()
        tmp.update({
            "filepath": v,
            "realpath": DATA['config']['FILE_PATH'] + v,
            "create_time": get_timestamp(),
        })
        find = db.table('task').where('filepath=? and realpath=?', (tmp['filepath'], tmp['realpath'],)).find()
        if find:
            print_info('【%s】已存在任务队列中，跳过' % tmp['filepath'])
        else:
            create_task(tmp)

if not DATA['config']['MULTITHREADING']:
    DATA['config']['MAX_WORKERS'] = 1


def thread(task):
    drive = client.upload_file(task)
    drive.finish_time = get_timestamp()
    drive.spend_time = drive.finish_time - drive.start_time
    if drive.status != 1:
        print_error(os.path.basename(drive.filepath) + ' 上传失败')
    client.save_task(drive)


def distribute_thread(tasks):
    if not DATA['config']['MULTITHREADING']:
        for task in tasks:
            thread(task)
    else:
        with ThreadPoolExecutor(max_workers=int(DATA['config']['MAX_WORKERS'])) as executor:
            future_list = []
            for task in tasks:
                # 提交线程
                future = executor.submit(thread, task)
                future_list.append(future)

            wait(future_list, return_when=ALL_COMPLETED)


while True:
    client.tasks = load_task()
    if len(client.tasks) <= 0:
        if not DATA['config']['RESIDENT']:
            break
        else:
            print_info('当前无任务，等待新的任务队列中', 0)
            time.sleep(5)
    distribute_thread(client.tasks)
