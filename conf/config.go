package conf

import "github.com/sirupsen/logrus"

type (
	Config struct {
		Debug    bool `json:"debug"`
		Transfers    uint64 `json:"transfers"`
		AliDrive struct {
			RefreshToken string `mapstructure:"refresh_token"`
			DriveId      string `mapstructure:"drive_id"`
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
