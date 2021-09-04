#!/usr/bin/python3
# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | main.py
# +-------------------------------------------------------------------
# | Author: Pluto <i@abcyun.cc>
# +-------------------------------------------------------------------

import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor

from AliyunDrive import AliyunDrive
from Client import Client
from common import DATA, print_error, get_db, get_timestamp, print_info, load_task, create_task, suicide, ctrl_c

if __name__ != '__main__':
    suicide(0)


signal.signal(signal.SIGINT, ctrl_c)
signal.signal(signal.SIGTERM, ctrl_c)

client = Client()
# 数据库初始化
client.init_database()
# 配置信息初始化
client.init_config()
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
        # 允许同一目录文件重复上传
        if DATA['config']['ALLOW_REPEAT']:
            create_task(tmp)
        else:
            find = db.table('task').where('filepath=? and realpath=?', (tmp['filepath'], tmp['realpath'],)).find()
            if find:
                print_info('【%s】已存在任务队列中，跳过' % tmp['filepath'])
            else:
                create_task(tmp)


def thread(task):
    drive = client.upload_file(task)
    drive.finish_time = get_timestamp()
    drive.spend_time = drive.finish_time - drive.start_time
    if drive.status != 1:
        print_error(os.path.basename(drive.filepath) + ' 上传失败')
    client.save_task(drive)


def distribute_thread(tasks):
    if not DATA['config']['MULTITHREADING'] or int(DATA['config']['MAX_WORKERS']) <= 0:
        for task in tasks:
            thread(task)
    else:
        with ThreadPoolExecutor(max_workers=int(DATA['config']['MAX_WORKERS'])) as executor:
            for task in tasks:
                # 提交线程
                executor.submit(thread, task)


# 定时任务
def crontab():
    def crontab_tasks():
        # 定时刷新token
        (AliyunDrive(DATA['config']['DRIVE_ID'], DATA['config']['ROOT_PATH'],
                     DATA['config']['CHUNK_SIZE'])).token_refresh()

    time_period = DATA['time_period']
    crontab_tasks()
    while True:
        if time_period <= 0:
            try:
                crontab_tasks()
            except Exception as e:
                print_error(e.__str__())
            finally:
                time_period = DATA['time_period']
        else:
            time_period -= 1
        time.sleep(1)


(ThreadPoolExecutor()).submit(crontab)

is_RESIDENT = DATA['config']['RESIDENT']
while True:
    client.tasks = load_task()
    if len(client.tasks) <= 0:
        if not is_RESIDENT:
            suicide(0)
        else:
            print_info('当前无任务，等待新的任务队列中', 0)
            time.sleep(5)
            continue
    distribute_thread(client.tasks)
