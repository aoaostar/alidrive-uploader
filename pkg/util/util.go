package util

import (
	"crypto/md5"
	"crypto/sha1"
	"encoding/base64"
	"encoding/hex"
	"golang.org/x/net/html"
	"io"
	"math"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
)

func GetSha1Code(data string) string {
	h := sha1.New()
	h.Write([]byte(data))
	return hex.EncodeToString(h.Sum(nil))
}

func GetProofCode(accessToken string, realpath string) (ProofCode, error) {
	var proofCode ProofCode
	file, err := os.Open(realpath)
	if err != nil {
		return proofCode, err
	}
	h := sha1.New()
	_, err = io.Copy(h, file)
	if err != nil {
		return proofCode, err
	}
	proofCode.Sha1 = hex.EncodeToString(h.Sum(nil))
	escape := url.QueryEscape(accessToken)
	if err != nil {
		return proofCode, err
	}
	buffa := html.UnescapeString(escape)
	m := md5.New()
	m.Write([]byte(buffa))
	hashMd5 := hex.EncodeToString(m.Sum(nil))
	stat, err := os.Stat(realpath)
	filesize := stat.Size()
	parseInt, err := strconv.ParseUint(hashMd5[0:16], 16, 64)
	if err != nil {
		return ProofCode{}, err
	}
	start := int64(parseInt % uint64(filesize))
	end := int64(math.Min(float64(start+8), float64(filesize)))

	_, err = file.Seek(start, 0)

	if err != nil {
		return ProofCode{}, err
	}
	var buffb = make([]byte, end-start)
	_, _ = file.Read(buffb)
	encoding := base64.StdEncoding.EncodeToString(buffb)
	proofCode.ProofCode = encoding
	return proofCode, nil
}
func GetFileContentType(out *os.File) (string, error) {

	buffer := make([]byte, 512)
	_, err := out.Read(buffer)
	if err != nil {
		return "", err
	}
	contentType := http.DetectContentType(buffer)
	return contentType, nil
}

func GetAllFiles(path string) ([]string, error) {
	var files []string
	err := filepath.Walk(path, func(p string, info os.FileInfo, err error) error {
		if !info.IsDir() {
			files = append(files, p)
		}
		return nil
	})
	return files, err
}

func TruncateText(str string, max int) string {
	length := len(str)
	if length-max > 3 {
		l := int(math.Min(float64(max), float64(length)))
		ru := []rune(str)
		str = string(ru[:l]) + "..."
	}
	return str
}
