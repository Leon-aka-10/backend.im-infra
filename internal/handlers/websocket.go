package handlers

import (
    "encoding/json"
    "log"
    "net/http"
    "github.com/gin-gonic/gin"
    "github.com/gorilla/websocket"
    "websocket-git/internal/models"
    "websocket-git/internal/services"
)

type WebSocketHandler struct {
    upgrader         websocket.Upgrader
    namespaceService *services.NamespaceService
    testService      *services.TestService
}

func NewWebSocketHandler(ns *services.NamespaceService, ts *services.TestService) *WebSocketHandler {
    return &WebSocketHandler{
        upgrader: websocket.Upgrader{
            ReadBufferSize:  1024,
            WriteBufferSize: 1024,
            CheckOrigin: func(r *http.Request) bool {
                return true
            },
        },
        namespaceService: ns,
        testService:      ts,
    }
}

func (h *WebSocketHandler) HandleConnection(c *gin.Context) {
    conn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
    if err != nil {
        log.Printf("Failed to upgrade connection: %v", err)
        return
    }
    defer conn.Close()

    log.Printf("New WebSocket connection established from %s", c.Request.RemoteAddr)

    for {
        _, rawMessage, err := conn.ReadMessage()
        if err != nil {
            log.Printf("Error reading message: %v", err)
            break
        }

        var gitMsg models.GitMessage
        if err := json.Unmarshal(rawMessage, &gitMsg); err != nil {
            log.Printf("Invalid message format: %v", err)
            sendError(conn, "Invalid message format")
            continue
        }

        // Handle namespace operations
        nsResult, err := h.namespaceService.HandleNamespace(gitMsg.ChatID, gitMsg.UserID, gitMsg.ProjectType)
        if err != nil {
            log.Printf("Namespace error: %v", err)
            sendError(conn, "Namespace error: "+err.Error())
            continue
        }

        namespace, ok := nsResult["namespace"].(string)
        if !ok || namespace == "" {
            log.Printf("Invalid namespace response: %v", nsResult)
            sendError(conn, "Invalid namespace received")
            continue
        }

        // Execute tests
        testResult, err := h.testService.RunTests(namespace, gitMsg.RepoURL, gitMsg.CommitHash, gitMsg.TestCmd)
        if err != nil {
            log.Printf("Test error: %v", err)
            sendError(conn, "Test execution failed: "+err.Error())
            continue
        }

        // Send combined response
        response := models.Response{
            Type: "test_results",
            Payload: map[string]interface{}{
                "namespace_status": nsResult,
                "test_results":     testResult,
            },
        }

        if err := conn.WriteJSON(response); err != nil {
            log.Printf("Error sending response: %v", err)
            break
        }
    }
}

func sendError(conn *websocket.Conn, message string) {
    response := models.Response{
        Type: "error",
        Payload: map[string]interface{}{
            "message": message,
        },
    }
    conn.WriteJSON(response)
}