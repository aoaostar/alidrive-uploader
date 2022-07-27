package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/alidrive"
	"fmt"
	"github.com/jessevdk/go-flags"
	"os"
)

func InitFlags() {

	parser := flags.NewParser(conf.Opt, flags.HelpFlag|flags.PassDoubleDash)
	_, err := parser.Parse()

	if conf.Opt.Refresh {
		refresh()
		os.Exit(0)
	}
	if e, ok := err.(*flags.Error); ok {
		if e.Type == flags.ErrHelp {
			parser.WriteHelp(os.Stdout)
			os.Exit(0)
		} else {
			fmt.Println(e)
			os.Exit(1)
		}
	}
}

func refresh() {

	InitConfig()
	InitLog()
	drive := alidrive.New(alidrive.Instance{
		RefreshToken: conf.Conf.AliDrive.RefreshToken,
		DriveId:      conf.Conf.AliDrive.DriveId,
		AccessToken:  "",
		ParentPath:   "root",
		Proxy:        conf.Conf.Proxy,
	})
	if err := drive.RefreshToken(); err != nil {
		conf.Output.Panic(err)
	}
	os.Exit(0)
}
