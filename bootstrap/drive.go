package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/alidrive"
	"github.com/sirupsen/logrus"
)

func TreeFolders(drive *alidrive.AliDrive, remotePath string, dirs map[string]string) {

	var err error
	drive.Instance.ParentPath, err = drive.CreateFolders(conf.Conf.AliDrive.RootPath+"/"+remotePath, "root")
	logrus.Debugf(drive.Instance.ParentPath)
	if err != nil {
		logrus.Panic(err)
		return
	}
	for k := range dirs {
		if k == "." || k == "/" || k == "\\" {
			dirs[k] = drive.Instance.ParentPath
			continue
		}
		dirs[k], err = drive.CreateFolders(k, drive.Instance.ParentPath)
		if err != nil {
			logrus.Panic(err)
			return
		}
	}
}
