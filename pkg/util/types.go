package util

import (
	"github.com/vbauerster/mpb/v7"
	"os"
)

type Json map[string]interface{}
type FileStream struct {
	File       *os.File
	Size       uint64
	ParentPath string
	Name       string
	MIMEType   string
	ReadlPath  string
	Bar        *mpb.Bar
}

type ProofCode struct {
	Sha1      string `json:"sha1"`
	ProofCode string `json:"proof_code"`
}

type Option struct {
	Debug     *bool   `short:"d" long:"debug" description:"Debug模式"`
	Transfers *uint64 `short:"t" long:"transfers" description:"同时上传文件个数"`
	Config    string  `short:"c" long:"config" description:"配置文件路径" default:"config.yaml"`
	Version   func()  `short:"v" long:"version" description:"输出版本信息"`
	AliDrive  struct {
		DriveId      string `long:"drive_id" description:"驱动id"`
		RefreshToken string `long:"refresh_token" description:"刷新令牌"`
		RootPath     string `long:"root_path" description:"根目录路径"`
	}
	Positional struct {
		LocalPath  string `positional-arg-name:"LocalPath" short:"i" long:"local" description:"本地文件路径" required:"true"`
		RemotePath string `positional-arg-name:"RemotePath" short:"o" long:"remote" description:"远程文件路径" default:"/"`
	} `positional-args:"true" required:"true"`
}
