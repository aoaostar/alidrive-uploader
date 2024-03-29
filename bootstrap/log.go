package bootstrap

import (
	"alidrive_uploader/conf"
	"fmt"
	"github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"
	"io"
	"os"
	"runtime"
)

func InitLog() {
	logWriter := &lumberjack.Logger{
		Filename:   conf.APP_PATH + "logs/alidrive.log", //日志文件位置
		MaxSize:    5,                                   // 单文件最大容量,单位是MB
		MaxBackups: 3,                                   // 最大保留过期文件个数
		MaxAge:     7,                                   // 保留过期文件的最大时间间隔,单位是天
		Compress:   false,                               // 是否需要压缩滚动日志, 使用的 gzip 压缩
		LocalTime:  true,
	}
	logrusFormatter := &logrus.TextFormatter{
		ForceColors:     true,
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
	}
	conf.Output.SetFormatter(logrusFormatter)
	conf.Output.SetOutput(io.MultiWriter(os.Stdout, logWriter))
	logrus.SetFormatter(logrusFormatter)
	logrus.SetOutput(logWriter)
	if conf.Conf.Debug {
		logrus.SetLevel(logrus.DebugLevel)
		conf.Output.SetLevel(logrus.DebugLevel)
		logrus.SetReportCaller(true)
		conf.Output.SetReportCaller(true)
	} else {
		logrus.SetLevel(logrus.InfoLevel)
		conf.Output.SetLevel(logrus.InfoLevel)
	}

	conf.Output.Infoln(fmt.Sprintf(`
+---------------------------------------------------------------------------------------+
        ___       ___       ___       ___       ___       ___       ___       ___   
       /\  \     /\__\     /\  \     /\  \     /\  \     /\  \     /\__\     /\  \  
      /::\  \   /:/  /    _\:\  \   /::\  \   /::\  \   _\:\  \   /:/ _/_   /::\  \ 
     /::\:\__\ /:/__/    /\/::\__\ /:/\:\__\ /::\:\__\ /\/::\__\ |::L/\__\ /::\:\__\
     \/\::/  / \:\  \    \::/\/__/ \:\/:/  / \;:::/  / \::/\/__/ |::::/  / \:\:\/  /
       /:/  /   \:\__\    \:\__\    \::/  /   |:\/__/   \:\__\    L;;/__/   \:\/  / 
       \/__/     \/__/     \/__/     \/__/     \|__|     \/__/               \/__/  

               Version: %s Runtime: %s/%s Go Version: %s
+---------------------------------------------------------------------------------------+
`, conf.VERSION, runtime.GOOS, runtime.GOARCH, runtime.Version()))
}
