# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 阿里云盘上传类
# +-------------------------------------------------------------------
# | Author: Pluto <i@abcyun.cc>
# +-------------------------------------------------------------------

import json
import math
import os
import requests
from tqdm import tqdm

from common import DATA, LOCK_TOKEN_REFRESH
import common

requests.packages.urllib3.disable_warnings()

"""
status: 0：未上传，1：上传成功，2：正在上传，-1：上传失败
"""


class AliyunDrive:
    def __init__(self, drive_id, root_path, chunk_size=10485760):
        self.status = 0
        self.create_time = 0
        self.start_time = common.get_timestamp()
        self.finish_time = 0
        self.spend_time = 0
        self.drive_id = drive_id
        self.root_path = root_path
        self.chunk_size = chunk_size
        self.filepath = None
        self.realpath = None
        self.filename = None
        self.hash = None
        self.part_info_list = []
        self.part_upload_url_list = []
        self.upload_id = 0
        self.file_id = 0
        self.part_number = 0
        self.filesize = 0
        self.headers = {
            'authorization': DATA['access_token'],
            'content-type': 'application/json;charset=UTF-8'
        }
        self.id = None

    def load_task(self, task):
        tmp = [
            "id",
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
        if task['drive_id'] == '' or int(task['drive_id']) == 0:
            task['drive_id'] = self.__getattribute__('drive_id')
        for v in tmp:
            self.__setattr__(v, task[v])

    def load_file(self, filepath, realpath):
        self.filepath = filepath
        self.realpath = realpath
        self.filename = os.path.basename(self.realpath)
        self.print('【{filename}】正在校检文件中，耗时与文件大小有关'.format(filename=self.filename), 'info')
        self.hash = common.get_hash(self.realpath)
        self.filesize = os.path.getsize(self.realpath)

        self.part_info_list = []
        for i in range(0, math.ceil(self.filesize / self.chunk_size)):
            self.part_info_list.append({
                'part_number': i + 1
            })

        message = '''=================================================
        文件名：{filename}
        hash：{hash}
        文件大小：{filesize}
        文件路径：{filepath}
=================================================
'''.format(filename=self.filename, hash=self.hash, filesize=self.filesize, filepath=self.realpath)
        self.print(message, 'info')

    def token_refresh(self):
        LOCK_TOKEN_REFRESH.acquire()
        try:
            data = {"refresh_token": DATA['config']['REFRESH_TOKEN'],'Grant_Type':'refresh_token'}
            post = requests.post(
                'https://auth.aliyundrive.com/v2/account/token',
                data=json.dumps(data),
                headers={
                    'content-type': 'application/json;charset=UTF-8'
                },
                verify=False,
                timeout=3
            )
            try:
                post_json = post.json()
                # 刷新配置中的token
                common.set_config('REFRESH_TOKEN', post_json['refresh_token'])

            except Exception as e:
                self.print('refresh_token已经失效', 'warn')
                raise e

            DATA['access_token'] = post_json['access_token']
            self.headers = {
                'authorization': DATA['access_token'],
                'content-type': 'application/json;charset=UTF-8'
            }
            DATA['config']['REFRESH_TOKEN'] = post_json['refresh_token']
        finally:
            LOCK_TOKEN_REFRESH.release()
        return True

    def create(self, parent_file_id):
        create_data = {
            "drive_id": self.drive_id,
            "part_info_list": self.part_info_list,
            "parent_file_id": parent_file_id,
            "name": self.filename,
            "type": "file",
            "check_name_mode": "auto_rename",
            "size": self.filesize,
            "content_hash": self.hash,
            "content_hash_name": 'sha1'
        }
        # 覆盖已有文件
        if DATA['config']['OVERWRITE']:
            create_data['check_name_mode'] = 'refuse'
        request_post = requests.post(
            'https://api.aliyundrive.com/v2/file/create',
            # 'https://api.aliyundrive.com/adrive/v2/file/createWithFolders',
            data=json.dumps(create_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = request_post.json()
        if not self.check_auth(requests_post_json):
            return self.create(parent_file_id)
        # 覆盖已有文件
        if DATA['config']['OVERWRITE'] and requests_post_json.get('exist'):
            if self.recycle(requests_post_json.get('file_id')):
                self.print('【%s】原有文件回收成功' % self.filename, 'info')
                self.print('【%s】重新上传新文件中' % self.filename, 'info')
                return self.create(parent_file_id)

        self.part_upload_url_list = requests_post_json.get('part_info_list', [])
        self.file_id = requests_post_json.get('file_id')
        self.upload_id = requests_post_json.get('upload_id')
        common.save_task(self.id, {
            'drive_id': self.drive_id,
            'file_id': self.file_id,
            'upload_id': self.upload_id,
        })
        return requests_post_json

    def get_upload_url(self):
        self.print('【%s】上传地址已失效正在获取新的上传地址' % self.filename, 'info')
        requests_data = {
            "drive_id": self.drive_id,
            "file_id": self.file_id,
            "part_info_list": self.part_info_list,
            "upload_id": self.upload_id,
        }
        requests_post = requests.post(
            'https://api.aliyundrive.com/v2/file/get_upload_url',
            data=json.dumps(requests_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = requests_post.json()
        if not self.check_auth(requests_post_json):
            return self.get_upload_url()
        self.print('【%s】上传地址刷新成功' % self.filename, 'info')
        return requests_post_json.get('part_info_list')

    def upload(self):
        with open(self.realpath, "rb") as f:
            task_log_id = common.log('正在上传【%s】0%%' % self.filename, self.id, 'info')
            with tqdm.wrapattr(f, "read", desc='正在上传【%s】' % self.filename, miniters=1,
                               initial=self.part_number * self.chunk_size,
                               total=self.filesize,
                               ascii=True
                               ) as fs:

                while self.part_number < len(self.part_upload_url_list):
                    upload_url = self.part_upload_url_list[self.part_number]['upload_url']
                    total_size = min(self.chunk_size, self.filesize)
                    fs.seek(self.part_number * total_size)
                    res = requests.put(
                        url=upload_url,
                        data=common.read_in_chunks(fs, 16 * 1024, total_size),
                        verify=False,
                        timeout=None
                    )
                    if 400 <= res.status_code < 600:
                        common_get_xml_value = common.get_xml_tag_value(res.text, 'Message')
                        if common_get_xml_value == 'Request has expired.':
                            self.part_upload_url_list = self.get_upload_url()
                            continue
                        common_get_xml_value = common.get_xml_tag_value(res.text, 'Code')
                        if common_get_xml_value == 'PartNotSequential':
                            self.part_number -= 1
                            continue
                        elif common_get_xml_value == 'PartAlreadyExist':
                            pass
                        else:
                            self.print(res.text, 'error')
                            # res.raise_for_status()
                            return False
                    self.part_number += 1
                    common.update_task_log(task_log_id,
                                           '正在上传【%s】%.2f%%' % (
                                               self.filename, ((self.part_number * total_size) / self.filesize) * 100))
                    udata = {
                        "part_number": self.part_number,
                    }
                    common.save_task(self.id, udata)

        return True

    def complete(self):
        complete_data = {
            "drive_id": self.drive_id,
            "file_id": self.file_id,
            "upload_id": self.upload_id
        }
        complete_post = requests.post(
            'https://api.aliyundrive.com/v2/file/complete', json.dumps(complete_data),
            headers=self.headers,
            verify=False
        )

        requests_post_json = complete_post.json()
        if not self.check_auth(requests_post_json):
            return self.complete()
        self.finish_time = common.get_timestamp()
        self.spend_time = self.finish_time - self.start_time

        if 'file_id' in requests_post_json:
            self.print('【{filename}】上传成功！消耗{s}秒'.format(filename=self.filename, s=self.spend_time), 'success')
            return True
        else:
            self.print('【{filename}】上传失败！消耗{s}秒'.format(filename=self.filename, s=self.spend_time), 'warn')
            return False

    def create_folder(self, folder_name, parent_folder_id):
        create_data = {
            "drive_id": self.drive_id,
            "parent_file_id": parent_folder_id,
            "name": folder_name,
            "check_name_mode": "refuse",
            "type": "folder"
        }
        requests_post = requests.post(
            'https://api.aliyundrive.com/adrive/v2/file/createWithFolders',
            data=json.dumps(create_data),
            headers=self.headers,
            verify=False
        )

        requests_post_json = requests_post.json()
        if not self.check_auth(requests_post_json):
            return self.create_folder(folder_name, parent_folder_id)
        return requests_post_json.get('file_id')

    def get_parent_folder_id(self, filepath):
        self.print('检索目录中', 'info')
        filepath_split = (self.root_path + filepath.lstrip(os.sep)).split(os.sep)
        del filepath_split[len(filepath_split) - 1]
        path_name = os.sep.join(filepath_split)
        if path_name not in DATA['folder_id_dict']:
            parent_folder_id = 'root'
            parent_folder_name = os.sep
            if len(filepath_split) > 0:
                for folder in filepath_split:
                    if folder in ['', 'root']:
                        continue
                    parent_folder_id = self.create_folder(folder, parent_folder_id)
                    parent_folder_name = parent_folder_name.rstrip(os.sep) + os.sep + folder
                    DATA['folder_id_dict'][parent_folder_name] = parent_folder_id
        else:
            parent_folder_id = DATA['folder_id_dict'][path_name]
            self.print('已存在目录，无需创建', 'info')

        self.print('目录id获取成功{parent_folder_id}'.format(parent_folder_id=parent_folder_id), 'info')
        return parent_folder_id

    def recycle(self, file_id):
        # https://api.aliyundrive.com/v2/batch
        requests_data = {
            "requests": [
                {
                    "body": {
                        "drive_id": self.drive_id,
                        "file_id": file_id
                    },
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "id": file_id,
                    "method": "POST",
                    "url": "/recyclebin/trash"
                }
            ],
            "resource": "file"
        }
        requests_post = requests.post(
            'https://api.aliyundrive.com/v2/batch',
            data=json.dumps(requests_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = requests_post.json()
        if not self.check_auth(requests_post_json):
            return self.recycle(file_id)
        return True

    def check_auth(self, response_json):
        if response_json.get('code') == 'AccessTokenInvalid':
            self.print('AccessToken已失效，尝试刷新AccessToken中', 'info')
            if self.token_refresh():
                self.print('AccessToken刷新成功，准备返回', 'info')
                return False
            self.print('无法刷新AccessToken，准备退出', 'error')
        if 'code' in response_json.keys():
            self.print(response_json, 'error')
            common.suicide()
        return True

    def print(self, message, print_type='info'):
        func = 'print_' + print_type
        return getattr(common, func)(message, self.id)
