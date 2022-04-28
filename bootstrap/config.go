package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/util"
	"github.com/sirupsen/logrus"
	"math"
)

func InitConfig() {

	var configPath = conf.Opt.Config
	if !util.FileExist(configPath) {
		configPath = conf.APP_PATH + conf.Opt.Config
	}
	// 指定配置文件路径
	conf.VipConfig.SetConfigFile(configPath)
	// 查找并读取配置文件
	if err := conf.VipConfig.ReadInConfig(); err != nil {
		logrus.Fatalf("读取配置出错: %s \n", err)
	}
	if err := conf.VipConfig.Unmarshal(&conf.Conf); err != nil {
		logrus.Fatalf("解析配置出错: %s \n", err)
	}
	if conf.Opt.Debug != nil {
		conf.Conf.Debug = *conf.Opt.Debug
	}

	if conf.Opt.Transfers != nil {
		conf.Conf.Transfers = *conf.Opt.Transfers
	}
	//最小任务数 1
	conf.Conf.Transfers = uint64(math.Max(float64(conf.Conf.Transfers), 1))

	if conf.Opt.AliDrive.DriveId != "" {
		conf.Conf.AliDrive.DriveId = conf.Opt.AliDrive.DriveId
	}
	if conf.Opt.AliDrive.RefreshToken != "" {
		conf.Conf.AliDrive.RefreshToken = conf.Opt.AliDrive.RefreshToken
	}
	if conf.Opt.AliDrive.RootPath != "" {
		conf.Conf.AliDrive.RootPath = conf.Opt.AliDrive.RootPath
	}
}
