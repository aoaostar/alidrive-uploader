package conf

import (
	"alidrive_uploader/pkg/util"
	"fmt"
	"github.com/spf13/viper"
	"os"
)

const (
	VERSION = "v2.0"
)

var (
	Conf      = new(Config)
	VipConfig = viper.New()
	Opt       = &util.Option{
		Version: func() {
			fmt.Printf("Alidrive Uploader %v", VERSION)
			os.Exit(0)
		},
	}
)
