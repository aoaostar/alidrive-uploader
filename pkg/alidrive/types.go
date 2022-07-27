package alidrive

import "time"

type (
	RespError struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	}
	TokenResp struct {
		AccessToken  string `json:"access_token"`
		RefreshToken string `json:"refresh_token"`
	}
	Instance struct {
		RefreshToken string
		DriveId      string
		AccessToken  string
		ParentPath   string
		Proxy        string
	}
	PartInfo struct {
		PartNumber uint64 `json:"part_number"`
		PartSize   uint64 `json:"part_size"`
	}
	PartInfoResp struct {
		PartNumber        int    `json:"part_number"`
		UploadUrl         string `json:"upload_url"`
		InternalUploadUrl string `json:"internal_upload_url"`
		ContentType       string `json:"content_type"`
	}
	CreateWithFoldersResp struct {
		ParentFileId string         `json:"parent_file_id"`
		PartInfoList []PartInfoResp `json:"part_info_list"`
		UploadId     string         `json:"upload_id"`
		RapidUpload  bool           `json:"rapid_upload"`
		Type         string         `json:"type"`
		FileId       string         `json:"file_id"`
		DomainId     string         `json:"domain_id"`
		DriveId      string         `json:"drive_id"`
		FileName     string         `json:"file_name"`
		EncryptMode  string         `json:"encrypt_mode"`
		Location     string         `json:"location"`
	}
	GetUploadUrlResp struct {
		DomainId     string         `json:"domain_id"`
		DriveId      string         `json:"drive_id"`
		FileId       string         `json:"file_id"`
		PartInfoList []PartInfoResp `json:"part_info_list"`
		UploadId     string         `json:"upload_id"`
		CreateAt     time.Time      `json:"create_at"`
	}
	CreateFoldersResp struct {
		ParentFileId string `json:"parent_file_id"`
		Type         string `json:"type"`
		FileId       string `json:"file_id"`
		DomainId     string `json:"domain_id"`
		DriveId      string `json:"drive_id"`
		FileName     string `json:"file_name"`
		EncryptMode  string `json:"encrypt_mode"`
	}
)
