#!/usr/bin/env bash

hash tar uname grep curl head

OS="$(uname)"
PROXY="https://ghproxy.com/"

case $OS in
  Linux)
    OS='linux'
    ;;
  Darwin)
    OS='darwin'
    ;;
  *)
    echo 'OS not supported'
    exit 2
    ;;
esac

ARCH="$(uname -m)"
case $ARCH in
  x86_64|amd64)
    ARCH='amd64'
    ;;
  aarch64)
    ARCH='arm64'
    ;;
  i?86|x86)
    ARCH='386'
    ;;
  arm*)
    ARCH='arm'
    ;;
  *)
    echo 'OS type not supported'
    exit 2
    ;;
esac


if [[ $1 == "-y" ]]; then
  echo "使用加速代理"
elif [[ $1 == "-n" ]]; then
  echo "不使用加速代理"
  PROXY=""
elif [[ $(curl -m 10 -s https://ipapi.co/json | grep 'China') != "" ]]; then
  echo "根据ipapi.co提供的信息，当前IP可能在中国"
  read -e -r -p "是否选用使用加速代理完成安装? [Y/n] " input
  case $input in
  [yY][eE][sS] | [yY])
    echo "使用加速代理"
    ;;

  [nN][oO] | [nN])
    echo "不使用加速代理"
    PROXY=""
    ;;
  *)
    echo "使用加速代理"
    ;;
  esac
fi

Install()
{
	echo '正在下载阿里云盘上传工具...'
  CORE_DOWNLOAD_URL=$PROXY$(curl -fsSL https://api.github.com/repos/aoaostar/alidrive-uploader/releases/latest | grep "browser_download_url.*$OS.*$ARCH" | cut -d '"' -f 4)
  curl -L "$CORE_DOWNLOAD_URL" | tar -xz
	echo '================================================'
	echo '阿里云盘上传工具下载完成'
}

Install