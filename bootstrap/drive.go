package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/alidrive"
	"alidrive_uploader/pkg/util"
	"github.com/vbauerster/mpb/v7"
	"math"
	"sync"
	"time"
)

var sm = sync.Map{}

func TreeFolders(drive *alidrive.AliDrive, remotePath string, dirs map[string]string) {

	var err error
	drive.Instance.ParentPath, err = drive.CreateFolders(conf.Conf.AliDrive.RootPath+"/"+remotePath, "root")
	conf.Output.Debugf(drive.Instance.ParentPath)
	if err != nil {
		conf.Output.Panic(err)
		return
	}
	var wg sync.WaitGroup
	p := mpb.New(mpb.WithWaitGroup(&wg), mpb.WithRefreshRate(300*time.Millisecond))
	bar := util.NewMpbExecute(p, "获取远程目录信息", int64(len(dirs)))
	workersNum := int(math.Min(float64(conf.Conf.Transfers), float64(len(dirs))))
	dirPath := make(chan string, workersNum)
	wg.Add(workersNum)
	for i := 0; i < workersNum; i++ {
		go func() {
			defer wg.Done()
			createFolder(dirPath, drive, bar)
		}()
	}
	for k := range dirs {
		dirPath <- k
	}
	close(dirPath)
	p.Wait()
	sm.Range(func(key, value interface{}) bool {
		dirs[key.(string)] = value.(string)
		return true
	})
}
func createFolder(dirPath chan string, drive *alidrive.AliDrive, bar *mpb.Bar) {
	for dir := range dirPath {
		if dir == "." {
			sm.Store(dir, drive.Instance.ParentPath)
			bar.Increment()
			continue

		}
		//重试n次
		for i := 0; i < 4; i++ {
			id, err := drive.CreateFolders(dir, drive.Instance.ParentPath)
			if err != nil {
				if i == 3 {
					conf.Output.Panic(err)
				}
				conf.Output.Warnf("第%+v次重试", i+1)
				continue
			}
			sm.Store(dir, id)
			bar.Increment()
			break
		}
	}
}
