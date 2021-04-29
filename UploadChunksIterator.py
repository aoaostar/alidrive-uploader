# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 阿里云盘上传Python3脚本
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import io
from typing import Union, Iterable
from tqdm.utils import CallbackIOWrapper


class UploadChunksIterator(Iterable):

    def __init__(
            self, file: Union[io.BufferedReader, CallbackIOWrapper],
            total_size: int,
            chunk_size: int = 10 * 1024,
    ):
        self.file = file
        self.chunk_size = chunk_size
        self.total_size = total_size
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index * self.chunk_size >= len(self):
            raise StopIteration
        data = self.file.read(self.chunk_size)
        self.index += 1
        if not data:
            raise StopIteration
        return data

    def __len__(self):
        return self.total_size
