package conf

import "github.com/sirupsen/logrus"

type (
	Config struct {
		Debug        bool   `json:"debug" mapstructure:"debug"`
		Transfers    uint64 `json:"transfers" mapstructure:"transfers"`
		Proxy        string `json:"proxy" mapstructure:"proxy"`
		MatchPattern string `json:"match_pattern" mapstructure:"match_pattern"`
		Retry        uint64 `json:"retry" mapstructure:"retry"`
		AliDrive     struct {
			DriveId      string `mapstructure:"drive_id"`
			RefreshToken string `mapstructure:"refresh_token"`
			RootPath     string `mapstructure:"root_path"`
		} `mapstructure:"ali_drive"`
	}
)

func SaveConfig() {

	err := VipConfig.WriteConfig()
	if err != nil {
		logrus.Panic(err)
		return
	}
}
