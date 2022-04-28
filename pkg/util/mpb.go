package util

import (
	"github.com/vbauerster/mpb/v7"
	"github.com/vbauerster/mpb/v7/decor"
)

func NewMpb(p *mpb.Progress, name string, total int64) *mpb.Bar {

	return p.New(total,
		mpb.BarStyle().Filler("#"),
		mpb.BarFillerClearOnComplete(),
		mpb.PrependDecorators(
			decor.Name(TruncateText(name, 25), decor.WCSyncSpace),
			decor.CountersKibiByte(" % .2f / % .2f ", decor.WCSyncSpace),
			decor.OnComplete(decor.Name("上传中", decor.WCSyncSpace), "上传完毕!"),
		),
		mpb.AppendDecorators(
			decor.AverageSpeed(decor.UnitKiB, "% .2f", decor.WCSyncSpace),
			decor.OnComplete(decor.Percentage(decor.WCSyncSpace), ""),
		),
	)
}
func NewMpbTask(p *mpb.Progress, name string, total int64) *mpb.Bar {
	return p.New(total,
		mpb.BarStyle().Filler("#"),
		mpb.PrependDecorators(
			decor.Name(name, decor.WCSyncSpace),
			decor.CountersNoUnit("%d / %d", decor.WCSyncSpace),
			decor.OnComplete(decor.Name("上传中", decor.WCSyncSpace), "上传完毕!"),
		),
		mpb.BarFillerClearOnComplete(),
		mpb.AppendDecorators(
			decor.OnComplete(decor.Percentage(decor.WCSyncSpace), ""),
		),
	)
}

func NewMpbExecute(p *mpb.Progress, name string, total int64) *mpb.Bar {
	return p.New(total,
		mpb.BarStyle().Filler("#"),
		mpb.PrependDecorators(
			decor.Name(name, decor.WCSyncSpace),
			decor.CountersNoUnit("%d / %d", decor.WCSyncSpace),
			decor.OnComplete(decor.Name("执行中", decor.WCSyncSpace), "执行完毕!"),
		),
		mpb.BarFillerClearOnComplete(),
		mpb.AppendDecorators(
			decor.OnComplete(decor.Percentage(decor.WCSyncSpace), ""),
		),
	)
}
