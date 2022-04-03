package bootstrap

import (
	"alidrive_uploader/conf"
	"github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"
	"io"
	"os"
)

func InitLog() {
	logWriter := &lumberjack.Logger{
		Filename:   "logs/alidrive.log", //日志文件位置
		MaxSize:    5,                   // 单文件最大容量,单位是MB
		MaxBackups: 3,                   // 最大保留过期文件个数
		MaxAge:     7,                   // 保留过期文件的最大时间间隔,单位是天
		Compress:   false,               // 是否需要压缩滚动日志, 使用的 gzip 压缩
		LocalTime:  true,
	}
	logrus.SetOutput(io.MultiWriter(os.Stdout, logWriter))
	logrus.SetFormatter(&logrus.TextFormatter{
		ForceColors:     true,
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
	})

	if *conf.Opt.Debug {
		logrus.SetLevel(logrus.DebugLevel)
		//logrus.SetReportCaller(true)
	} else {
		logrus.SetLevel(logrus.InfoLevel)
	}
}
