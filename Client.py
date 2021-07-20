# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | Client.py
# +-------------------------------------------------------------------
# | Author: Pluto <i@abcyun.cc>
# +-------------------------------------------------------------------

# 配置信息
import json
import os
import sqlite3
import sys

from AliyunDrive import AliyunDrive
from common import get_running_path, print_error, get_config, DATA, get_config_file_path, qualify_path, \
    get_all_file_relative, print_success, LOCK, get_db_file_path, save_task, get_timestamp, print_warn, date, \
    print_info


class Client():
    tasks = []
    database_file = get_db_file_path()

    def __init__(self):
        pass

    def __upload(self, drive):
        try:
            drive.upload()
        except Exception as e:
            status = False
            for index in range(DATA['config']['RETRY']):
                print_warn('【%s】正在尝试第%d次重试！' % (drive.filename, index), drive.id)
                if drive.upload():
                    status = True
                    break
            if not status:
                drive.status = -1
                return drive
        # 提交
        if drive.complete():
            drive.status = 1
        else:
            drive.status = -1
        return drive

    def init_config(self):
        config = {
            "REFRESH_TOKEN": "refresh_token",
            "DRIVE_ID": "drive_id",
            "ROOT_PATH": "root",
            "FILE_PATH": get_running_path(),
            "MULTITHREADING": False,
            "MAX_WORKERS": 5,
            "CHUNK_SIZE": 104857600,
            "RESUME": False,
            "OVERWRITE": False,
            "RETRY": 0,
            "RESIDENT": False,
        }
        if not os.path.exists(get_config_file_path()):
            print_error('请配置好config.json后重试')
            with open(get_config_file_path(), 'w') as f:
                f.write(json.dumps(config))
            sys.exit()
        try:
            config.update(get_config())
            DATA['config'] = config

        except Exception as e:
            print_error('请配置好config.json后重试')
            raise e

    def init_command_line_parameter(self):
        for k in range(len(sys.argv)):
            if sys.argv[k] == '--resident' or sys.argv[k] == '-r':
                DATA['config']['RESIDENT'] = True
                del sys.argv[k]
        # 命令分配
        if len(sys.argv) == 3:
            # 网盘保存路径
            DATA['config']['ROOT_PATH'] = qualify_path(sys.argv[2]).rstrip(os.sep)
            # 读取文件路径
            abspath = os.path.abspath(sys.argv[1])

        elif len(sys.argv) == 2:
            # 读取文件路径
            abspath = os.path.abspath(sys.argv[1])
        else:
            # 读取配置文件里的
            abspath = DATA['config']['FILE_PATH']

        DATA['config']['FILE_PATH'] = os.path.dirname(abspath)
        if os.path.isdir(abspath):
            # 目录上传
            self.tasks = get_all_file_relative(abspath)
            self.tasks = list(map(lambda x: os.path.basename(abspath) + os.sep + x, self.tasks))
        else:
            # 单文件上传
            self.tasks = [os.path.basename(abspath)]
        # 获取目录的父目录以上传该目录并且格式化目录

        DATA['config']['FILE_PATH'] = qualify_path(DATA['config']['FILE_PATH'])

    def init_database(self):
        conn = sqlite3.connect(self.database_file)
        cursor = conn.cursor()
        cursor.execute('''create table IF NOT EXISTS task
(
	id INTEGER
		primary key autoincrement,
	filepath TEXT default '' not null,
	realpath TEXT default '' not null,
	filesize INTEGER,
	hash TEXT default '' not null,
	status INTEGER default 0 not null,
	drive_id TEXT default '' not null,
	file_id TEXT default '' not null,
	upload_id TEXT default '' not null,
	part_number INTEGER default 0 not null,
	chunk_size INTEGER default 104857600 not null,
	create_time INTEGER default 0 not null,
	finish_time INTEGER default 0 not null,
	spend_time INTEGER default 0 not null
);''')
        cursor.execute('''create table IF NOT EXISTS task_log
(
    id          INTEGER not null
        constraint task_log_pk
            primary key autoincrement,
    task_id     INTEGER,
    content     TEXT    default '' not null,
    create_time INTEGER default 0 not null
);''')

    def upload_file(self, task):
        save_task(task['id'], {
            'status': 2
        })
        drive = AliyunDrive(DATA['config']['DRIVE_ID'], DATA['config']['ROOT_PATH'], DATA['config']['CHUNK_SIZE'])
        # 加载任务队列
        drive.load_task(task)
        # 刷新token
        drive.token_refresh()
        drive.load_file(task['filepath'], task['realpath'])
        # 创建目录
        LOCK.acquire()
        try:
            parent_folder_id = drive.get_parent_folder_id(drive.filepath)
        finally:
            LOCK.release()
        # 断点续传
        if DATA['config']['RESUME'] and DATA['config']['DRIVE_ID'] == task['drive_id']:
            if 0 not in [
                drive.drive_id,
                drive.part_number,
                drive.chunk_size,
            ] and not drive.file_id and not drive.upload_id:
                # 获取上传地址
                drive.part_upload_url_list = drive.get_upload_url()
                # 上传
                return self.__upload(drive)

        # 创建上传
        create_post_json = drive.create(parent_folder_id)
        if 'rapid_upload' in create_post_json and create_post_json['rapid_upload']:
            drive.finish_time = get_timestamp()
            drive.spend_time = drive.finish_time - drive.start_time
            print_success('【{filename}】秒传成功！消耗{s}秒'.format(filename=drive.filename, s=drive.spend_time), drive.id)
            drive.status = 1
            return drive
        # 上传
        return self.__upload(drive)

    def save_task(self, task):
        task_id = task.id
        tmp = [
            "filepath",
            "realpath",
            "filesize",
            "hash",
            "status",
            "create_time",
            "finish_time",
            "spend_time",
            "drive_id",
            "file_id",
            "upload_id",
            "part_number",
            "chunk_size",
        ]
        data = {}
        for v in tmp:
            data[v] = task.__getattribute__(v)
        return save_task(task_id, data)

    def print_config_info(self):
        s = ''
        for k in DATA['config'].keys():
            s += "\n\t\t%s：%s" % (k, DATA['config'][k])

        content = '''=================================================
        阿里云盘上传工具启动成功
        当前时间：%s%s
=================================================
''' % (date(get_timestamp()), s)
        print_info(content)
