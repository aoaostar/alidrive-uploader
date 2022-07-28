package conf

import (
	"alidrive_uploader/pkg/util"
	"fmt"
	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"
	"os"
	"path/filepath"
)

const (
	VERSION = "v2.2.1"
)

var executable, _ = os.Executable()
var symlinks, _ = filepath.EvalSymlinks(executable)

var APP_PATH = filepath.Dir(symlinks) + "/"

var (
	Conf      = new(Config)
	VipConfig = viper.New()
	Output    = logrus.New()
	Opt       = &util.Option{
		Version: func() {
			fmt.Printf("Alidrive Uploader %v", VERSION)
			os.Exit(0)
		},
		Clean: func() {
			err := os.RemoveAll(APP_PATH + "runtime/checker")
			if err != nil {
				fmt.Printf("清理缓存失败, %s", err.Error())
				os.Exit(1)
			}
			fmt.Print("清理缓存成功")
			os.Exit(0)
		},
	}
)
