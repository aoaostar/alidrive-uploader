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
	VERSION = "v2.1"
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
	}
)
