## 阿里云盘上传脚本

* Author：Pluto
* Github：https://github.com/Hidove/aliyundrive-uploader

> 如有侵权，请联系我删除
>
> 禁止用于非法用途，违者后果自负

## 环境要求
* python3

## 使用方法
### 直接使用
<https://github.com/Hidove/aliyundrive-uploader/releases>
先下载对应系统版本，没有的需要自行编译
#### windows/Linux系统
* 下载文件后解压
* 配置好config.json文件
* 打开命令行 
  * Win 输入`main.exe`
  * Linux 输入`./main`
* 命令行参数与py脚本使用方式一致
* 为方便使用可加入环境变量

### 脚本运行
```shell
git clone https://github.com/Hidove/aliyundrive-uploader.git
cd aliyundrive-uploader
pip install -r requirements.txt
```

如果执行`pip install`时提示`-bash: pip: command not found`
就是`pip`命令没有安装，执行下方命令安装即可，然后再执行即可

```shell
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
```

* 重命名`example.config.json`为`config.json`
* 填写好`config.json`的内容

![](https://z3.ax1x.com/2021/03/27/6zB8JA.png)

> 控制台快速获取代码

```js
var data = JSON.parse(localStorage.getItem('token'));
console.log(`refresh_token  =>  ${data.refresh_token}
default_drive_id  =>  ${data.default_drive_id}
`);
```
```json
{
  "REFRESH_TOKEN": "refresh_token",
  "DRIVE_ID": "drive_id",
  "ROOT_PATH": "网盘目录",
  "FILE_PATH": "D:\\Pictures\\",
  "MULTITHREADING": false,
  "MAX_WORKERS": 5,
  "CHUNK_SIZE": 104857600,
  "RESUME": false,
  "OVERWRITE": false,
  "RETRY": 0,
  "RESIDENT": false
}
```
| 参数             | 注释                               |   值           |
|-----------------|-----------------------------------|----------------|
| REFRESH_TOKEN  | 阿里云盘刷新的token                  |                |   
| DRIVE_ID       | 阿里云盘驱动ID，目前不知道做何使用的，可能后续官方有新想法吧 | |  
| ROOT_PATH      | 阿里云盘目录                         |    我的照片     |  
| FILE_PATH      | 文件夹目录，填写绝对路径               | D:\\Pictures\\ | 
| MULTITHREADING | 是否启用多线程                       | true/false     |
| MAX_WORKERS    | 线程池最大线程数，请根据自己机器填写     |     5           |  
| CHUNK_SIZE     | 分块上传大小，请根据自己机器填写，单位：字节 | 104857600     |   
| RESUME         | 断点续传，分块续传                  | true/false       |
| OVERWRITE      | 覆盖同名文件，会将原文件放入回收站     | true/false       |
| RETRY          | 上传失败重试次数                   |     0            |
| RESIDENT      | 是否启用常驻运行，不间断运行，会监控数据库内的任务队列| true/false       |

##### 运行
```shell
chmod +x main.py
```
> 多文件上传

```shell
python3 main.py
```
```shell
python3 main.py /www/wwwroot/download/
```
> 单文件上传

```shell
python3 main.py /www/lixiaoen.jpg
```
> 指定上传目录

```shell
python3 main.py /www/lixiaoen.jpg /Backup
```
> 常驻运行

```
python3 main.py --resident
python3 main.py -r
```
> 指定上传目录并启动常驻运行

```
python3 main.py -r /www/lixiaoen.jpg /Backup
```
## 更新
```shell
cd ~/aliyundrive-uploader
git fetch --all 
git reset --hard origin/master 
git pull
```

## 编译
> 需要配合conda或virtualenv使用，请自行学习相关知识

### 以virtualenv为例
* 安装virtualenv
```shell
pip install virtualenv
```
```shell
virtualenv aliyundrive  # 创建一个虚拟环境，虚拟环境的名字为aliyundrive
source ENV/bin/activate # 激活虚拟环境
pip install -r requirements.txt # 安装依赖
pip install pyinstaller # 安装依赖
```
* 执行编译命令
```shell
pyinstaller -F main.py
```
* 结果
> 打开dist目录即可看到打包的可执行文件了

## 文件解读
* `config.json` 
  * 脚本配置文件
* `/log`
  * 脚本执行记录
* `db.db`
  * sqlite数据库文件

## 支持
> 觉得写得不错可以给我打赏哦

![](https://z3.ax1x.com/2021/03/26/6Xh5ex.md.png)