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
	"net/http"
	"path/filepath"
	"strings"
)

type (
	AliDrive struct {
		Instance Instance
	}
)

var client = resty.New()

func (drive *AliDrive) RefreshToken() error {
	url := "https://auth.aliyundrive.com/v2/account/token"
	var resp TokenResp
	var e RespError
	_, err := client.R().
		SetBody(util.Json{"refresh_token": drive.Instance.RefreshToken, "grant_type": "refresh_token"}).
		SetResult(&resp).
		SetError(&e).
		Post(url)
	if err != nil {
		return err
	}
	logrus.Debugf("%+v,%+v", resp, e)

	if e.Code != "" {
		return fmt.Errorf("刷新token失败: %s", e.Message)
	}
	drive.Instance.RefreshToken, drive.Instance.AccessToken = resp.RefreshToken, resp.AccessToken
	return nil
}

func (drive *AliDrive) Upload(file util.FileStream) error {

	url := "https://api.aliyundrive.com/adrive/v2/file/createWithFolders"
	var resp CreateWithFoldersResp
	var e RespError

	const CHUNKSIZE int64 = 10 * 1024 * 1024
	var total = uint64(math.Ceil(float64(file.Size) / float64(CHUNKSIZE)))

	var partInfoList = make([]PartInfo, 0, total)
	var i uint64
	for i = 0; i < total; i++ {
		partInfoList = append(partInfoList, PartInfo{
			PartNumber: i + 1,
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
		SetAuthToken(drive.Instance.AccessToken).
		SetBody(&createWithFoldersBody).
		SetResult(&resp).
		SetError(&e).
		Post(url)
	if err != nil {
		return err
	}
	logrus.Debugf("%+v,%+v", resp, e)
	if e.Code != "" && e.Code != "PreHashMatched" {
		if e.Code == "AccessTokenInvalid" {
			err := drive.RefreshToken()
			if err != nil {
				conf.SaveConfig()
				return drive.Upload(file)
			} else {
				return err
			}
		}
		return errors.New(e.Message)
	}
	//proof_code
	if e.Code == "PreHashMatched" {
		proofCode, err := util.GetProofCode(drive.Instance.AccessToken, file.ReadlPath)
		if err != nil {
			return err
		}
		delete(createWithFoldersBody, "pre_hash")
		createWithFoldersBody["content_hash_name"] = "sha1"
		createWithFoldersBody["content_hash"] = proofCode.Sha1
		createWithFoldersBody["proof_code"] = proofCode.ProofCode
		createWithFoldersBody["proof_version"] = "v1"
		logrus.Debug("createWithFoldersBody", createWithFoldersBody)
		_, err = client.R().
			SetAuthToken(drive.Instance.AccessToken).
			SetBody(&createWithFoldersBody).
			SetResult(&resp).
			SetError(&e).
			Post(url)
		logrus.Debugf("%+v,%+v", resp, e)
		if err != nil {
			return err
		}
		if e.Code != "" && e.Code != "PreHashMatched" {
			return errors.New(e.Message)
		}
		if resp.RapidUpload {
			return nil
		}
	}

	if len(resp.PartInfoList) != int(total) {
		return errors.New("上传地址为空，无法上传")
	}
	//正式上传
	if _, err = file.File.Seek(0, 0); err != nil {
		return err
	}
	for i = 0; i < total; i++ {
		req, err := http.NewRequest(http.MethodPut, resp.PartInfoList[i].UploadUrl, file.Bar.ProxyReader(io.LimitReader(file.File, CHUNKSIZE)))
		if err != nil {
			return err
		}
		c := http.Client{}
		res, err := c.Do(req)
		if err != nil {
			return err
		}
		if res.StatusCode == 403 {
			readAll, err := ioutil.ReadAll(res.Body)
			_ = res.Body.Close()
			if err != nil {
				return err
			}
			if err := xml.Unmarshal(readAll, &e); err != nil {
				return err
			}
			logrus.Debugf("%+v", e)
			if e.Code == "AccessTokenInvalid" {
				err := drive.RefreshToken()
				if err != nil {
					return err
				}
				conf.SaveConfig()
				i--
				continue
			}
			if e.Message == "Request has expired." {
				getUploadUrlResp := GetUploadUrlResp{}
				var getUploadUrlBody = util.Json{
					"drive_id":       drive.Instance.DriveId,
					"file_id":        resp.FileId,
					"part_info_list": partInfoList,
					"upload_id":      resp.UploadId,
				}
				_, err := client.R().SetResult(&getUploadUrlResp).SetError(&e).SetBody(getUploadUrlBody).
					SetAuthToken(drive.Instance.AccessToken).
					Post("https://api.aliyundrive.com/v2/file/get_upload_url")
				if err != nil {
					return err
				}
				if e.Code != "" {
					return errors.New(e.Message)
				}
				resp.PartInfoList = getUploadUrlResp.PartInfoList
				i--
				continue
			}
		}
	}
	//complete
	var resp2 = util.Json{}
	_, err = client.R().SetResult(&resp2).SetBody(util.Json{
		"drive_id":  drive.Instance.DriveId,
		"file_id":   resp.FileId,
		"upload_id": resp.UploadId,
	}).SetAuthToken(drive.Instance.AccessToken).SetError(&e).
		Post("https://api.aliyundrive.com/v2/file/complete")
	if err != nil {
		return err
	}
	logrus.Debugf("%+v,%+v", resp2, e)
	if e.Code != "" {
		return fmt.Errorf("%+v", e.Message)
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
		_, err := client.R().SetAuthToken(drive.Instance.AccessToken).SetError(&e).SetBody(&body).SetResult(&resp).
			Post("https://api.aliyundrive.com/adrive/v2/file/createWithFolders")
		if err != nil {
			return parentFileId, err
		}
		logrus.Debugf("%+v,%+v", resp, e)
		if e.Code != "" {
			return parentFileId, errors.New(e.Message)
		}
		parentFileId = resp.FileId
	}
	return parentFileId, nil
}
