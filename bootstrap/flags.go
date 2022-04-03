package bootstrap

import (
	"alidrive_uploader/conf"
	"github.com/jessevdk/go-flags"
	"os"
)

func InitFlags() {
	_, err := flags.Parse(conf.Opt)

	if e, ok := err.(*flags.Error); ok {
		if e.Type == flags.ErrHelp {
			os.Exit(0)
		} else {
			os.Exit(1)
		}
	}
}
