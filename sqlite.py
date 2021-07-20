import sys

import sqlite3
import os, re, time


def get_running_path(path=''):
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable) + path
    elif __file__:
        return os.path.dirname(__file__) + path


class sqlite():
    # ------------------------------
    # 数据库操作类 For sqlite3
    # ------------------------------
    DB_FILE = None  # 数据库文件
    DB_CONN = None  # 数据库连接对象
    DB_TABLE = ""  # 被操作的表名称
    OPT_WHERE = ""  # where条件
    OPT_LIMIT = ""  # limit条件
    OPT_ORDER = ""  # order条件
    OPT_GROUPBY = ""  # group by条件
    OPT_FIELD = "*"  # field条件
    OPT_PARAM = ()  # where值
    __LOCK = get_running_path() + 'sqlite_lock.pl'

    def __init__(self):
        self.DB_FILE = 'data/default.db'

    def GetConn(self):
        # 取数据库对象
        try:
            if self.DB_CONN == None:
                self.DB_CONN = sqlite3.connect(self.DB_FILE)
                if sys.version_info[0] == 3:
                    self.DB_CONN.text_factory = lambda x: str(x,
                                                              encoding="utf-8", errors='ignore')
                else:
                    self.DB_CONN.text_factory = lambda x: unicode(x,
                                                                  "utf-8", "ignore")
        except Exception as ex:
            print(ex)
            return "error: " + str(ex)

    def dbfile(self, path):
        if not os.path.isfile(path):
            raise RuntimeError("数据库文件不存在。")
        self.DB_FILE = path
        return self

    def table(self, table):
        # 设置表名
        self.DB_TABLE = table
        return self

    def where(self, where, param):
        # WHERE条件
        if where:
            self.OPT_WHERE = " WHERE " + where
            self.OPT_PARAM = self.__to_tuple(param)
        return self

    def __to_tuple(self, param):
        # 将参数转换为tuple
        if type(param) != tuple:
            if type(param) == list:
                param = tuple(param)
            else:
                param = (param,)
        return param

    def order(self, order):
        # ORDER条件
        if len(order):
            self.OPT_ORDER = " ORDER BY " + order
        return self

    def groupby(self, group):
        if len(group):
            self.OPT_GROUPBY = " GROUP BY " + group
        return self

    def limit(self, limit):
        # LIMIT条件
        if len(limit):
            self.OPT_LIMIT = " LIMIT " + limit
        return self

    def field(self, field):
        # FIELD条件
        if len(field):
            self.OPT_FIELD = field
        return self

    def log(self, msg):
        log_file = "/www/server/panel/logs/error.log"
        if sys.version_info[0] == 3:
            with open(log_file, "a", encoding="utf-8") as fp:
                fp.write("\n" + msg)
        else:
            with open(log_file, "a") as fp:
                fp.write("\n" + msg)

    def select(self):
        # 查询数据集
        self.GetConn()
        try:
            self.__get_columns()
            sql = "SELECT " + self.OPT_FIELD + " FROM " + self.DB_TABLE + self.OPT_WHERE + self.OPT_GROUPBY + self.OPT_ORDER + self.OPT_LIMIT
            result = self.DB_CONN.execute(sql, self.OPT_PARAM)
            data = result.fetchall()
            # 构造字典系列
            if self.OPT_FIELD != "*":
                fields = self.__format_field(self.OPT_FIELD.split(','))
                tmp = []
                for row in data:
                    i = 0
                    tmp1 = {}
                    for key in fields:
                        tmp1[key] = row[i]
                        i += 1
                    tmp.append(tmp1)
                    del (tmp1)
                data = tmp
                del (tmp)
            else:
                # 将元组转换成列表
                tmp = list(map(list, data))
                data = tmp
                del (tmp)
            self.__close()
            return data
        except Exception as ex:
            return "error: " + str(ex)

    def get(self):
        self.__get_columns()
        return self.select()

    def __format_field(self, field):
        fields = []
        for key in field:
            s_as = re.search('\s+as\s+', key, flags=re.IGNORECASE)
            if s_as:
                as_tip = s_as.group()
                key = key.split(as_tip)[1]
            fields.append(key)
        return fields

    def __get_columns(self):
        if self.OPT_FIELD == '*':
            tmp_cols = self.query('PRAGMA table_info(' + self.DB_TABLE + ')', ())
            cols = []
            for col in tmp_cols:
                if len(col) > 2: cols.append(col[1])
            if len(cols) > 0: self.OPT_FIELD = ','.join(cols)

    def getField(self, keyName):
        # 取回指定字段
        try:
            result = self.field(keyName).select()
            if len(result) != 0:
                return result[0][keyName]
            return result
        except:
            return None

    def setField(self, keyName, keyValue):
        # 更新指定字段
        return self.save(keyName, (keyValue,))

    def find(self):
        # 取一行数据
        try:
            result = self.limit("1").select()
            if len(result) == 1:
                return result[0]
            return result
        except:
            return None

    def count(self):
        # 取行数
        key = "COUNT(*)"
        data = self.field(key).select()
        try:
            return int(data[0][key])
        except:
            return 0

    def add(self, keys, param):
        # 插入数据
        self.write_lock()
        self.GetConn()
        self.DB_CONN.text_factory = str
        try:
            values = ""
            for key in keys.split(','):
                values += "?,"
            values = values[0:len(values) - 1]
            sql = "INSERT INTO " + self.DB_TABLE + "(" + keys + ") " + "VALUES(" + values + ")"
            result = self.DB_CONN.execute(sql, self.__to_tuple(param))
            id = result.lastrowid
            self.__close()
            self.DB_CONN.commit()
            self.rm_lock()
            return id
        except Exception as ex:
            return "error: " + str(ex)

    # 插入数据
    def insert(self, pdata):
        if not pdata: return False
        keys, param = self.__format_pdata(pdata)
        return self.add(keys, param)

    # 更新数据
    def update(self, pdata):
        if not pdata: return False
        keys, param = self.__format_pdata(pdata)
        return self.save(keys, param)

    # 构造数据
    def __format_pdata(self, pdata):
        keys = pdata.keys()
        keys_str = ','.join(keys)
        param = []
        for k in keys: param.append(pdata[k])
        return keys_str, tuple(param)

    def addAll(self, keys, param):
        # 插入数据
        self.write_lock()
        self.GetConn()
        self.DB_CONN.text_factory = str
        try:
            values = ""
            for key in keys.split(','):
                values += "?,"
            values = values[0:len(values) - 1]
            sql = "INSERT INTO " + self.DB_TABLE + "(" + keys + ") " + "VALUES(" + values + ")"
            result = self.DB_CONN.execute(sql, self.__to_tuple(param))
            self.rm_lock()
            return True
        except Exception as ex:
            return "error: " + str(ex)

    def commit(self):
        self.__close()
        self.DB_CONN.commit()

    def save(self, keys, param):
        # 更新数据
        self.write_lock()
        self.GetConn()
        self.DB_CONN.text_factory = str
        try:
            opt = ""
            for key in keys.split(','):
                opt += key + "=?,"
            opt = opt[0:len(opt) - 1]
            sql = "UPDATE " + self.DB_TABLE + " SET " + opt + self.OPT_WHERE
            # 处理拼接WHERE与UPDATE参数
            tmp = list(self.__to_tuple(param))
            for arg in self.OPT_PARAM:
                tmp.append(arg)
            self.OPT_PARAM = tuple(tmp)
            result = self.DB_CONN.execute(sql, self.OPT_PARAM)
            self.__close()
            self.DB_CONN.commit()
            self.rm_lock()
            return result.rowcount
        except Exception as ex:
            return "error: " + str(ex)

    def delete(self, id=None):
        # 删除数据
        self.write_lock()
        self.GetConn()
        try:
            if id:
                self.OPT_WHERE = " WHERE id=?"
                self.OPT_PARAM = (id,)
            sql = "DELETE FROM " + self.DB_TABLE + self.OPT_WHERE
            result = self.DB_CONN.execute(sql, self.OPT_PARAM)
            self.__close()
            self.DB_CONN.commit()
            self.rm_lock()
            return result.rowcount
        except Exception as ex:
            return "error: " + str(ex)

    def execute(self, sql, param=(), auto_commit=True):
        # 执行SQL语句返回受影响行
        self.write_lock()
        self.GetConn()
        try:
            result = self.DB_CONN.execute(sql, self.__to_tuple(param))
            if auto_commit:
                self.DB_CONN.commit()
            self.rm_lock()
            return result.rowcount
        except Exception as ex:
            return "error: " + str(ex)

    # 是否有锁
    def is_lock(self):
        n = 0
        while os.path.exists(self.__LOCK):
            n += 1
            if n > 100:
                self.rm_lock()
                break
            time.sleep(0.01)

    # 写锁
    def write_lock(self):
        self.is_lock()
        with(open(self.__LOCK, 'w+'))as f:
            f.write("True")

    # 解锁
    def rm_lock(self):
        if os.path.exists(self.__LOCK):
            os.remove(self.__LOCK)

    def query(self, sql, param=()):
        # 执行SQL语句返回数据集
        self.GetConn()
        try:
            result = self.DB_CONN.execute(sql, self.__to_tuple(param))
            # self.log("result:" + str(result))
            # 将元组转换成列表
            data = list(map(list, result))
            return data
        except Exception as ex:
            return "error: " + str(ex)

    def create(self, name):
        # 创建数据表
        self.write_lock()
        self.GetConn()
        with(open('data/' + name + '.sql', 'rb')) as f:
            script = f.read().decode('utf-8')
        result = self.DB_CONN.executescript(script)
        self.DB_CONN.commit()
        self.rm_lock()
        return result.rowcount

    def fofile(self, filename):
        # 执行脚本
        self.write_lock()
        self.GetConn()
        with(open(filename, 'rb')) as f:
            script = f.read().decode('utf-8')
        result = self.DB_CONN.executescript(script)
        self.DB_CONN.commit()
        self.rm_lock()
        return result.rowcount

    def __close(self):
        # 清理条件属性
        self.OPT_WHERE = ""
        self.OPT_FIELD = "*"
        self.OPT_ORDER = ""
        self.OPT_LIMIT = ""
        self.OPT_GROUPBY = ""
        self.OPT_PARAM = ()

    def close(self):
        # 释放资源
        try:
            self.DB_CONN.close()
            self.DB_CONN = None
        except:
            pass
