## 阿里云盘上传脚本

* Author：李小恩
* Github：https://github.com/Hidove/aliyundrive-uploader

> 如有侵权，请联系我删除

## 环境要求
* python3

## 使用方法
* 重命名`example.config.json`为`config.json`
* 填写好`config.json`的内容

![](https://z3.ax1x.com/2021/03/26/6XhFqx.png)

```json
{
  "REFRESH_TOKEN": "refresh_token",
  "DRIVE_ID": "drive_id",
  "PARENT_FILE_ID": "目录ID，根目录就填root",
  "FILE_PATH": "填目录地址，绝对路径：D:\\Pictures\\"
}
```
```shell
chmod +x main.py && python3 main.py
```

## 文件解读

* `config.json`脚本配置文件
* `filelist.json`脚本上传任务记录文件

## 支持

![](https://z3.ax1x.com/2021/03/26/6Xh5ex.md.png)