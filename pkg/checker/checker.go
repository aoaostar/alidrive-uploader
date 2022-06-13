package checker

import (
	"crypto/md5"
	"encoding/hex"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

type Checker struct {
	localDir        string
	existMap        map[string]interface{}
	existMapLock    sync.RWMutex
	existConfigFile string
	isDir           bool
}

func NewChecker(localDir, confDir string) *Checker {
	checker := Checker{
		localDir: localDir,
		existMap: map[string]interface{}{},
		isDir:    false,
	}
	stat, err := os.Stat(localDir)
	if err != nil {
		return &checker
	}
	checker.isDir = stat.IsDir()
	if !checker.isDir {
		return &checker
	}
	hash := md5.Sum([]byte(localDir))
	hashMD5 := hex.EncodeToString(hash[:])[8:14]
	baseDir := strings.Trim(filepath.Base(localDir), "/")
	checker.existConfigFile = filepath.Join(confDir, baseDir+"."+hashMD5+".txt")
	existFiles, err := ioutil.ReadFile(checker.existConfigFile)
	if err != nil {
		return &checker
	}
	for _, f := range strings.Split(string(existFiles), "\n") {
		checker.existMap[f] = true
	}
	return &checker
}

func (checker *Checker) AddFile(file string) {
	checker.existMapLock.Lock()
	defer checker.existMapLock.Unlock()
	file = strings.Trim(strings.ReplaceAll(file, checker.localDir, ""), "/")
	checker.existMap[file] = true
}

func (checker *Checker) Save() {
	if !checker.isDir {
		return
	}
	var sb strings.Builder
	for file := range checker.existMap {
		sb.WriteString(file)
		sb.WriteString("\n")
	}
	ioutil.WriteFile(checker.existConfigFile, []byte(sb.String()), 0644)
}

func (checker *Checker) CheckExist(file string) bool {
	checker.existMapLock.RLock()
	defer checker.existMapLock.RUnlock()
	file = strings.Trim(strings.ReplaceAll(file, checker.localDir, ""), "/")
	if _, ok := checker.existMap[file]; ok {
		return true
	}
	return false
}
