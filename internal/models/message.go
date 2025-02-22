package models

type GitMessage struct {
    UserID      string `json:"userId"`
    ChatID      string `json:"chatId"`
    RepoURL     string `json:"repoURL"`
    CommitHash  string `json:"commitHash"`
    ProjectType string `json:"projectType"`
    TestCmd     string `json:"testCommand,omitempty"`
}

type Response struct {
    Type    string      `json:"type"`
    Payload interface{} `json:"payload"`
}