package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/alidrive"
	"alidrive_uploader/pkg/checker"
	"alidrive_uploader/pkg/util"
	"github.com/sirupsen/logrus"
	"github.com/vbauerster/mpb/v7"
	"math"
	"net"
	"os"
	"path/filepath"
	"sync"
	"time"
)

var errors = map[string]string{}
var successes = 0

var dirs = make(map[string]string, 0)

func Run() {
	var err error

	InitFlags()
	InitConfig()
	InitLog()

	conf.Opt.Positional.LocalPath, _ = filepath.Abs(conf.Opt.Positional.LocalPath)

	stat, err := os.Stat(conf.Opt.Positional.LocalPath)
	if err != nil {
		conf.Output.Panic(err)
		return
	}
	var allFiles []string
	if stat.IsDir() {
		allFiles, err = util.GetAllFiles(conf.Opt.Positional.LocalPath, conf.Conf.MatchPattern)
		if err != nil {
			conf.Output.Panic(err)
			return
		}
	} else {
		allFiles = []string{filepath.Base(conf.Opt.Positional.LocalPath)}
	}
	conf.Opt.Positional.LocalPath = filepath.Dir(conf.Opt.Positional.LocalPath) + "/"
	conf.Output.Infof("共计%d个文件", len(allFiles))

	drive := alidrive.New(alidrive.Instance{
		RefreshToken: conf.Conf.AliDrive.RefreshToken,
		DriveId:      conf.Conf.AliDrive.DriveId,
		AccessToken:  "",
		ParentPath:   "root",
		Proxy:        conf.Conf.Proxy,
	})

	conf.Output.Infof("正在获取AccessToken")
	if err := drive.RefreshToken(); err != nil {
		conf.Output.Panic(err)
		return
	}

	conf.Output.Infof("正在生成目录")
	var files []util.FileStream

	//建立目录结构
	localChecker := checker.NewChecker(
		conf.Opt.Positional.LocalPath,
		conf.APP_PATH+"runtime/checker",
	)
	for _, fp := range allFiles {
		if localChecker.CheckExist(fp) {
			continue
		}
		//目录
		dir := filepath.ToSlash(filepath.Dir(fp))
		file, err := readFileInfo(conf.Opt.Positional.LocalPath + fp)
		file.LocalChecker = localChecker
		if err != nil {
			conf.Output.Panic(err)
			return
		}
		file.ParentPath = dir
		files = append(files, file)
		dirs[dir] = ""
	}
	var StartTime = time.Now()
	defer func() {
		conf.Output.Infof("上传完毕！共计%d个文件，失败文件个数：%d个，耗时：%v", len(files), len(files)-successes, time.Since(StartTime))
		localChecker.Save()
	}()
	if len(files) <= 0 {
		return
	}

	TreeFolders(drive, conf.Opt.Positional.RemotePath, dirs)

	wg := sync.WaitGroup{}
	p := mpb.New(mpb.WithWaitGroup(&wg), mpb.WithRefreshRate(300*time.Millisecond))

	//文件数量进度条
	taskBar := util.NewMpbTask(p, "任务列表", int64(len(files)))

	workersNum := int(math.Min(float64(len(files)), float64(conf.Conf.Transfers)))
	jobs := make(chan util.FileStream, workersNum)

	for i := 0; i < workersNum; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			transfer(jobs, taskBar, p, drive, dirs)
		}()
	}
	for _, file := range files {
		jobs <- file
	}
	close(jobs)
	p.Wait()
}

func transfer(jobs chan util.FileStream, taskBar *mpb.Bar, p *mpb.Progress, drive *alidrive.AliDrive, dirs map[string]string) {

	for file := range jobs {
		logrus.Infof("[%v]正在上传", file.Name)
		file.File, _ = os.Open(file.ReadlPath)
		file.Bar = util.NewMpb(p, file.Name, int64(file.Size))
		file.ParentPath = dirs[file.ParentPath]
		var err error
		for i := 0; i <= int(conf.Conf.Retry); i++ {
			err = drive.Upload(file)
			if e, ok := err.(net.Error); ok && e.Timeout() {
				logrus.Errorf("[%s] %s", file.Name, err.Error())
				logrus.Warnf("[%s] 第%d次重试中", file.Name, i+1)
				continue
			}
			break
		}
		file.Bar.Abort(true)
		if err != nil {
			logrus.Errorf("[%v]上传失败: %v", file.Name, err)
			errors[file.ReadlPath] = err.Error()
		} else {
			file.LocalChecker.AddFile(file.ReadlPath)
			logrus.Infof("[%v]上传成功", file.Name)
			successes++
		}
		taskBar.Increment()
		_ = file.File.Close()
	}
}
func readFileInfo(fp string) (util.FileStream, error) {

	var fs util.FileStream
	open, err := os.Open(fp)
	defer open.Close()
	if err != nil {
		return fs, err
	}
	stat, err := os.Stat(fp)

	if err != nil {
		return fs, err
	}
	contentType := util.GetFileContentType(open)
	abs, err := filepath.Abs(fp)
	if err != nil {
		return fs, err
	}
	return util.FileStream{
		File:       nil,
		Size:       uint64(stat.Size()),
		ParentPath: "root",
		Name:       stat.Name(),
		MIMEType:   contentType,
		ReadlPath:  abs,
	}, nil
}
