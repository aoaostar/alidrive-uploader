package alidrive

import (
	"alidrive_uploader/conf"
	"alidrive_uploader/pkg/util"
	"encoding/xml"
	"errors"
	"fmt"
	"github.com/go-resty/resty/v2"
	"github.com/sirupsen/logrus"
	"io"
	"io/ioutil"
	"math"
	"net"
	"net/http"
	"path/filepath"
	"strings"
	"time"
)

type (
	AliDrive struct {
		Instance Instance
	}
)

var client = resty.New()

func New(instance Instance) *AliDrive {
	if instance.Proxy != "" {
		instance.Proxy = strings.TrimRight(instance.Proxy, "/") + "/"
	}
	client.OnBeforeRequest(func(c *resty.Client, request *resty.Request) error {
		request.URL = instance.Proxy + request.URL
		return nil
	})
	return &AliDrive{instance}
}

func (drive *AliDrive) RefreshToken() error {
	logrus.Infof("[刷新token] 正在刷新")
	url := "https://auth.aliyundrive.com/v2/account/token"
	var resp TokenResp
	var e RespError
	for i := 0; i <= int(conf.Conf.Retry); i++ {
		_, err := client.R().
			SetBody(util.Json{"refresh_token": drive.Instance.RefreshToken, "grant_type": "refresh_token"}).
			SetResult(&resp).
			SetError(&e).
			Post(url)
		if err != nil {
			if err2, ok := err.(net.Error); ok && err2.Timeout() {
				logrus.Errorf("[刷新token] %s", err.Error())
				logrus.Warnf("[刷新token] 第%d次重试中", i+1)
				continue
			}
			return err
		}
		break
	}
	logrus.Debugf("%+v", resp)
	logrus.Debugf("%+v", e)

	if e.Code != "" {
		return fmt.Errorf("[刷新token] 失败: %s: %s", e.Code, e.Message)
	}
	drive.Instance.RefreshToken, drive.Instance.AccessToken = resp.RefreshToken, resp.AccessToken
	client.SetAuthToken(drive.Instance.AccessToken)
	conf.SaveConfig()
	logrus.Infof("[刷新token] 成功")
	return nil
}

func (drive *AliDrive) Upload(file util.FileStream) error {

	url := "https://api.aliyundrive.com/adrive/v2/file/createWithFolders"
	var resp CreateWithFoldersResp
	var e RespError

	var ChunkSize uint64 = 5 << 20
	var total = uint64(math.Ceil(float64(file.Size) / float64(ChunkSize)))
	for {
		if ChunkSize >= 5<<30 {
			ChunkSize = 5 << 30
			total = uint64(math.Ceil(float64(file.Size) / float64(ChunkSize)))
			break
		}
		if total >= 10000 {
			ChunkSize += 5 << 20
			total = uint64(math.Ceil(float64(file.Size) / float64(ChunkSize)))
			continue
		}
		break
	}

	var partInfoList = make([]PartInfo, 0, total)
	var i uint64
	for i = 0; i < total; i++ {
		//{
		//    "code": "InvalidResource.PartList",
		//    "message": "The resource part_list is not valid. part entity too small"
		//}
		ck := ChunkSize
		if i+1 == total {
			ck = file.Size - ChunkSize*(i-1)
		}
		partInfoList = append(partInfoList, PartInfo{
			PartNumber: i + 1,
			PartSize:   ck,
		})
	}
	var b = make([]byte, 1024)
	read, _ := file.File.Read(b)
	var preHash = util.GetSha1Code(string(b[:read]))

	var createWithFoldersBody = util.Json{
		"drive_id":        drive.Instance.DriveId,
		"part_info_list":  partInfoList,
		"parent_file_id":  file.ParentPath,
		"name":            file.Name,
		"type":            "file",
		"check_name_mode": "overwrite",
		"size":            file.Size,
		"pre_hash":        preHash,
	}
	//preHash
	_, err := client.R().
		SetBody(&createWithFoldersBody).
		SetResult(&resp).
		SetError(&e).
		Post(url)
	if err != nil {
		return err
	}
	logrus.Debugf("[%s] %+v", file.Name, createWithFoldersBody)
	logrus.Debugf("[%s] %+v", file.Name, resp)
	logrus.Debugf("[%s] %+v", file.Name, e)
	if e.Code != "" && e.Code != "PreHashMatched" {
		if e.Code == "AccessTokenInvalid" {
			if err := drive.RefreshToken(); err != nil {
				return drive.Upload(file)
			} else {
				return err
			}
		}
		return fmt.Errorf("%s: %s", e.Code, e.Message)
	}
	//proof_code
	if e.Code == "PreHashMatched" {
		proofCode, err := util.GetProofCode(drive.Instance.AccessToken, file.ReadlPath)
		if err != nil {
			return err
		}
		var e2 = RespError{}
		delete(createWithFoldersBody, "pre_hash")
		createWithFoldersBody["content_hash_name"] = "sha1"
		createWithFoldersBody["content_hash"] = proofCode.Sha1
		createWithFoldersBody["proof_code"] = proofCode.ProofCode
		createWithFoldersBody["proof_version"] = "v1"
		_, err = client.R().
			SetBody(&createWithFoldersBody).
			SetResult(&resp).
			SetError(&e2).
			Post(url)
		logrus.Debugf("[%s] %+v", file.Name, createWithFoldersBody)
		logrus.Debugf("[%s] %+v", file.Name, resp)
		logrus.Debugf("[%s] %+v", file.Name, e2)
		if err != nil {
			return err
		}
		if e2.Code != "" && e2.Code != "PreHashMatched" {
			return fmt.Errorf("%s: %s", e2.Code, e2.Message)
		}
		if resp.RapidUpload {
			logrus.Infof("[%s] 秒传成功，思密达~", file.Name)
			return nil
		}
	}

	if len(resp.PartInfoList) != int(total) {
		return errors.New("上传地址为空，无法上传")
	}
	//正式上传
	if _, err := file.File.Seek(0, io.SeekStart); err != nil {
		return err
	}
	//需要写入进度到日志的时期
	var progress = map[float64]bool{
		0.05: false,
		0.25: false,
		0.50: false,
		0.75: false,
		0.90: false,
		0.95: false,
		0.96: false,
		0.97: false,
		0.98: false,
		0.99: false,
		1.00: false,
	}

	for i = 0; i < total; i++ {
		var startTime = time.Now()
		for num := 0; num <= int(conf.Conf.Retry); num++ {
			if num > 0 {
				logrus.Warnf("[%s][upload] 第%d次重试中", file.Name, num)
			}
			if _, err := file.File.Seek(int64(ChunkSize*i), io.SeekStart); err != nil {
				return err
			}
			req, err := http.NewRequest(http.MethodPut, drive.Instance.Proxy+resp.PartInfoList[i].UploadUrl, file.Bar.ProxyReader(io.LimitReader(file.File, int64(ChunkSize))))
			if err != nil {
				return err
			}
			c := http.Client{}
			res, err := c.Do(req)
			if err != nil {
				//请求超时重试
				if err2, ok := err.(net.Error); ok && err2.Timeout() {
					logrus.Errorf("[%s] %s", file.Name, err.Error())
					continue
				}
				return err
			}
			if res.StatusCode == 403 {
				readAll, err := ioutil.ReadAll(res.Body)
				_ = res.Body.Close()
				if err != nil {
					return err
				}
				var e = RespError{}
				if err := xml.Unmarshal(readAll, &e); err != nil {
					return err
				}
				logrus.Debugf("[%s] %+v", file.Name, e)
				if e.Code == "AccessTokenInvalid" {
					if err := drive.RefreshToken(); err != nil {
						return err
					}
					num--
					continue
				}
				if e.Code == "AccessDenied" {
				GetUploadUrl:
					var e2 RespError
					var getUploadUrlResp = GetUploadUrlResp{}
					var getUploadUrlBody = util.Json{
						"drive_id":       drive.Instance.DriveId,
						"file_id":        resp.FileId,
						"part_info_list": partInfoList,
						"upload_id":      resp.UploadId,
					}
					if _, err := client.R().SetResult(&getUploadUrlResp).SetError(&e2).SetBody(getUploadUrlBody).
						Post("https://api.aliyundrive.com/v2/file/get_upload_url"); err != nil {
						//请求超时重试
						if err2, ok := err.(net.Error); ok && err2.Timeout() {
							logrus.Errorf("[%s][GetUploadUrl] %s", file.Name, err.Error())
							continue
						}
						return err
					}
					logrus.Debugf("[%s] %+v", file.Name, e2)
					if e2.Code == "AccessTokenInvalid" {
						if err := drive.RefreshToken(); err != nil {
							return err
						}
						goto GetUploadUrl
					}
					if e2.Code != "" {
						return fmt.Errorf("%s: %s", e2.Code, e2.Message)
					}
					resp.PartInfoList = getUploadUrlResp.PartInfoList
					num--
					continue
				}
			}

			// 大于 20 * ChunkSize 的文件才会输出进度到日志，默认100MB
			if total >= 20 {
				currentProgress := math.Floor(float64((i+1)*ChunkSize)/float64(file.Size)*100) / 100

				for k, v := range progress {
					if !v && currentProgress >= k {
						progress[k] = true
						duration := time.Since(startTime)
						logrus.Infof("[%s] 已上传 %s/%s, 上传速度 %s/s, 共用时 %v, %v%%",
							file.Name,
							util.FormatFileSize(float64((i+1)*ChunkSize)),
							util.FormatFileSize(float64(file.Size)),
							util.FormatFileSize(float64(ChunkSize)/duration.Seconds()),
							duration,
							currentProgress*100)
					}
				}
			}
			// 上传完毕break
			break
		}
	}
	//complete
	var resp2 = util.Json{}
	var e2 RespError
	for i := 0; i <= int(conf.Conf.Retry); i++ {
		_, err = client.R().SetResult(&resp2).SetBody(util.Json{
			"drive_id":  drive.Instance.DriveId,
			"file_id":   resp.FileId,
			"upload_id": resp.UploadId,
		}).SetError(&e2).
			Post("https://api.aliyundrive.com/v2/file/complete")
		if err != nil {
			//请求超时重试
			if err2, ok := err.(net.Error); ok && err2.Timeout() {
				logrus.Errorf("[%s][complete] %s", file.Name, err.Error())
				logrus.Errorf("[%s][complete] 第%d次重试中", file.Name, i+1)
				continue
			}
			return err
		}
		if e2.Code == "AccessTokenInvalid" {
			if err := drive.RefreshToken(); err != nil {
				i--
				continue
			} else {
				return err
			}
		}
		// complete完毕break
		break
	}
	logrus.Debugf("[%s] %+v", file.Name, resp2)
	logrus.Debugf("[%s] %+v", file.Name, e2)
	if e2.Code != "" {
		return fmt.Errorf("%s: %s", e2.Code, e2.Message)
	}
	if resp2["file_id"] == resp.FileId {
		return nil
	}
	return fmt.Errorf("%+v", resp2)
}

func (drive *AliDrive) CreateFolders(path string, rootPath string) (string, error) {

	path = filepath.ToSlash(path)
	split := strings.Split(path, "/")
	var parentFileId = rootPath
	for _, v := range split {
		if v == "" {
			continue
		}
		var e RespError
		var resp CreateFoldersResp
		var body = util.Json{
			"drive_id":        drive.Instance.DriveId,
			"parent_file_id":  parentFileId,
			"name":            v,
			"check_name_mode": "refuse",
			"type":            "folder",
		}
		_, err := client.R().SetError(&e).SetBody(&body).SetResult(&resp).
			Post("https://api.aliyundrive.com/adrive/v2/file/createWithFolders")
		if err != nil {
			return parentFileId, err
		}
		logrus.Debugf("%+v", resp)
		logrus.Debugf("%+v", e)
		if e.Code != "" {
			return parentFileId, fmt.Errorf("%s: %s", e.Code, e.Message)
		}
		parentFileId = resp.FileId
	}
	return parentFileId, nil
}
