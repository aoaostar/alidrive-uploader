package bootstrap

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/alidrive"
	"alidrive_uploader/pkg/util"
	"github.com/vbauerster/mpb/v7"
	"math"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type folderChan struct {
	pathname string
	id       *string
}

var tree map[string]interface{}

func TreeFolders(drive *alidrive.AliDrive, remotePath string, dirs map[string]string) {

	// 转化目录树
	tree = parseDir(dirs)

	var err error
	drive.Instance.ParentPath, err = drive.CreateFolders(conf.Conf.AliDrive.RootPath+"/"+remotePath, "root")
	conf.Output.Debugf(drive.Instance.ParentPath)
	if err != nil {
		conf.Output.Panic(err)
		return
	}
	var wg sync.WaitGroup
	p := mpb.New(mpb.WithWaitGroup(&wg), mpb.WithRefreshRate(300*time.Millisecond))
	bar := util.NewMpbExecute(p, "获取远程目录信息", int64(len(tree)))

	workersNum := int(math.Min(float64(conf.Conf.Transfers), float64(len(tree))))

	fc := make(chan folderChan, workersNum)
	wg.Add(workersNum)

	for i := 0; i < workersNum; i++ {
		go func() {
			defer wg.Done()
			createFolder(fc, drive, bar)
		}()
	}

	var treeFolderId func(dirs map[string]interface{}, parent string)
	treeFolderId = func(dirs map[string]interface{}, parent string) {
		for k, v := range dirs {

			if _, b := v.(string); !b {
				treeFolderId(v.(map[string]interface{}), parent+"/"+k)
			} else {
				fcTmp := folderChan{
					pathname: parent,
					id:       new(string),
				}
				dirs[k] = fcTmp.id
				fc <- fcTmp
			}
		}
	}
	treeFolderId(tree, "")
	close(fc)
	p.Wait()
	// 输出到目录id列表
	for k := range dirs {
		split := strings.Split(k, "/")
		tmp := tree
		for _, s := range split {
			if s != "" {
				if value, b := tmp[s]; b {
					tmp = value.(map[string]interface{})
				}
			}
		}
		dirs[k] = *tmp["__alidrive_id"].(*string)
	}
}
func createFolder(folderChan chan folderChan, drive *alidrive.AliDrive, bar *mpb.Bar) {
	for folder := range folderChan {
		folder.pathname = strings.TrimLeft(folder.pathname, "/")
		if folder.pathname == "." {
			*folder.id = drive.Instance.ParentPath
			bar.Increment()
			continue
		}
		// 从读取已有值
		split := strings.Split(folder.pathname, "/")
		var parentFolderId = drive.Instance.ParentPath
		var pathname = folder.pathname
		for i := 0; i < len(split); i++ {
			if v, b := tree[split[i]]; b {
				if v2, b2 := v.(map[string]interface{})["__alidrive_id"].(*string); b2 && *v2 != "" {
					parentFolderId = *v2
					pathname = strings.Join(split[i+1:], "/")
				}
			} else {
				break
			}
		}

		//重试n次
		for i := 0; i < 4; i++ {
			folderId, err := drive.CreateFolders(pathname, parentFolderId)
			if err != nil {
				if i == 3 {
					conf.Output.Panic(err, "  parentFolderId  ", parentFolderId)
				}
				conf.Output.Warnf("第%+v次重试", i+1)
				continue
			}
			*folder.id = folderId
			bar.Increment()
			break
		}
	}
}

func parseDir(dirs map[string]string) map[string]interface{} {
	var arr = make(map[string]interface{})
	for k, _ := range dirs {
		k = filepath.ToSlash(k)
		split := strings.Split(k, "/")
		for i, s := range split {
			if s == "" {
				split = append(split[:i], split[i+1:]...)
			}
		}
		var result = map[string]interface{}{
			"__alidrive_id": "__alidrive_id",
		}
		for i := len(split) - 1; i >= 0; i-- {
			result = map[string]interface{}{
				split[i]:        result,
				"__alidrive_id": "__alidrive_id",
			}
		}
		arr = mergeMap(arr, result)
	}
	return arr
}

func mergeMap(mObj ...map[string]interface{}) map[string]interface{} {
	newObj := map[string]interface{}{}
	for _, m := range mObj {
		for k, v := range m {
			if v1, b := v.(map[string]interface{}); b {
				if v2, b2 := newObj[k].(map[string]interface{}); b2 {
					newObj[k] = mergeMap(v2, v1)
					continue
				}
			}
			newObj[k] = v
		}
	}
	return newObj
}
