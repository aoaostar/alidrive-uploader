# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 阿里云盘上传类
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import json
import os
import time

import requests
from tqdm import tqdm

requests.packages.urllib3.disable_warnings()
from UploadChunksIterator import UploadChunksIterator
from common import print_warn, print_info, print_error, print_success, get_hash


class AliyunDrive:
    def __init__(self, drive_id, parent_file_id, refresh_token):
        self.drive_id = drive_id
        self.parent_file_id = parent_file_id
        self.refresh_token = refresh_token
        self.filepath = None
        self.filename = None
        self.hash = None

    def load_file(self, filepath):
        self.start_time = time.time()
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        print_info('【{filename}】正在校检文件中，耗时与文件大小有关'.format(filename=self.filename))
        self.hash = get_hash(self.filepath)
        self.filesize = os.path.getsize(self.filepath)
        message = '''=================================================
        文件名：{filename}
        hash：{hash}
        文件大小：{filesize}
        文件路径：{filepath}
=================================================
'''.format(filename=self.filename, hash=self.hash, filesize=self.filesize, filepath=self.filepath)
        print_info(message)

    def token_refresh(self):
        global post_json
        data = {"refresh_token": self.refresh_token}
        post = requests.post(
            'https://websv.aliyundrive.com/token/refresh',
            data=json.dumps(data),
            headers={
                'content-type': 'application/json;charset=UTF-8'
            },
            verify=False
        )
        try:
            post_json = post.json()
            # 刷新配置中的token
            with open(os.getcwd() + '/config.json', 'r') as f:
                config = json.loads(f.read())
            config['REFRESH_TOKEN'] = post_json['refresh_token']
            with open(os.getcwd() + '/config.json', 'w') as f:
                f.write(json.dumps(config))
                f.flush()

        except Exception as e:
            print_warn('refresh_token已经失效')
            print_warn(e)
            exit()

        access_token = post_json['access_token']
        self.headers = {
            'authorization': access_token
        }
        self.refresh_token = post_json['refresh_token']

    def create(self):
        create_data = {
            "auto_rename": True,
            "hash": self.hash,
            "drive_id": self.drive_id,
            "hidden": False,
            "name": self.filename,
            "parent_file_id": self.parent_file_id,
            "type": "file"
        }
        create_post = requests.post(
            'https://api.aliyundrive.com/v2/file/create',
            data=json.dumps(create_data),
            headers=self.headers,
            verify=False
        )
        create_post_json = create_post.json()
        if create_post_json.get('code') == 'AccessTokenInvalid':
            print_info('AccessToken已失效，尝试刷新AccessToken中')
            if self.token_refresh():
                print_info('AccessToken刷新成功，返回创建上传任务')
                self.create()
                return
            print_error('无法刷新AccessToken，准备退出')
            exit()
        return create_post_json

    def upload(self, upload_url):
        with open(self.filepath, "rb") as f:
            total_size = os.fstat(f.fileno()).st_size
            f = tqdm.wrapattr(f, "read", desc='正在上传', miniters=1, total=total_size, ascii=True)
            with f as f_iter:
                res = requests.put(
                    url=upload_url,
                    data=UploadChunksIterator(f_iter, total_size=total_size),
                    verify=False
                )
                res.raise_for_status()

    def complete(self, file_id, upload_id):
        complete_data = {
            "drive_id": self.drive_id,
            "file_id": file_id,
            "upload_id": upload_id
        }
        complete_post = requests.post(
            'https://api.aliyundrive.com/v2/file/complete', json.dumps(complete_data),
            headers=self.headers,
            verify=False
        )

        complete_post_json = complete_post.json()
        if complete_post_json.get('code') == 'AccessTokenInvalid':
            print_info('AccessToken已失效，尝试刷新AccessToken中')
            if self.token_refresh():
                print_info('AccessToken刷新成功，返回创建上传任务')
                self.complete(file_id, upload_id)
                return
            print_error('无法刷新AccessToken，准备退出')
            exit()
        s = time.time() - self.start_time
        if 'file_id' in complete_post_json:
            print_success('【{filename}】上传成功！消耗{s}秒'.format(filename=self.filename, s=s))
            return True
        else:
            print_warn('【{filename}】上传失败！消耗{s}秒'.format(filename=self.filename, s=s))
            return False
