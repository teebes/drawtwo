import Foundation

enum SocketStatus: String {
    case disconnected = "Disconnected"
    case connecting = "Connecting"
    case reconnecting = "Reconnecting"
    case connected = "Connected"
    case failed = "Failed"
}

@MainActor
final class DrawTwoWebSocket: ObservableObject {
    @Published private(set) var status: SocketStatus = .disconnected
    @Published private(set) var messagesReceived = 0
    @Published private(set) var lastMessage = "No messages yet."
    @Published private(set) var errorMessage: String?

    var onTextMessage: ((String) -> Void)?

    private var task: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var heartbeatTask: Task<Void, Never>?
    private var pongTimeoutTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var queuedMessages: [String] = []
    private var currentPath: String?
    private var currentAccessToken: String?
    private var currentGuestToken: String?
    private var currentHeartbeatEnabled = true
    private var intentionalDisconnect = false
    private var reconnectAttempts = 0

    private let maxReconnectAttempts = 10

    func connect(
        path: String,
        accessToken: String? = nil,
        guestToken: String? = nil,
        heartbeatEnabled: Bool = true
    ) {
        intentionalDisconnect = false
        reconnectAttempts = 0
        currentPath = path
        currentAccessToken = accessToken
        currentGuestToken = guestToken
        currentHeartbeatEnabled = heartbeatEnabled
        reconnectTask?.cancel()
        reconnectTask = nil

        closeSocket()
        openSocket(
            path: path,
            accessToken: accessToken,
            guestToken: guestToken,
            isReconnect: false
        )
    }

    private func openSocket(
        path: String,
        accessToken: String?,
        guestToken: String?,
        isReconnect: Bool
    ) {
        guard let url = makeURL(path: path, accessToken: accessToken, guestToken: guestToken) else {
            status = .failed
            errorMessage = "Could not build WebSocket URL."
            return
        }

        status = isReconnect ? .reconnecting : .connecting
        errorMessage = nil

        var request = URLRequest(url: url)
        request.setValue(AppConfig.backendBaseURL.absoluteString, forHTTPHeaderField: "Origin")
        request.setValue("Archetype-iOS/0.1", forHTTPHeaderField: "User-Agent")

        let socketTask = URLSession.shared.webSocketTask(with: request)
        task = socketTask
        socketTask.resume()
        status = .connected
        if currentHeartbeatEnabled {
            startHeartbeat(for: socketTask)
        }
        flushQueuedMessages()

        receiveTask = Task { [weak self, weak socketTask] in
            guard let self, let socketTask else { return }
            await self.receiveLoop(socketTask)
        }
    }

    func send(json: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(json) else {
            errorMessage = "Could not encode WebSocket command."
            return
        }

        do {
            let data = try JSONSerialization.data(withJSONObject: json)
            guard let text = String(data: data, encoding: .utf8) else {
                errorMessage = "Could not encode WebSocket command."
                return
            }
            send(text: text)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func sendPresence(active: Bool) {
        guard task != nil else {
            return
        }
        send(json: [
            "type": "client_presence",
            "active": active,
        ])
    }

    func send(text: String) {
        guard let task else {
            queuedMessages.append(text)
            errorMessage = "WebSocket is reconnecting. Command queued."
            return
        }

        Task {
            do {
                try await task.send(.string(text))
            } catch {
                await MainActor.run {
                    self.queuedMessages.append(text)
                    self.handleUnexpectedDisconnect(
                        from: task,
                        errorMessage: error.localizedDescription
                    )
                }
            }
        }
    }

    func disconnect() {
        intentionalDisconnect = true
        reconnectTask?.cancel()
        reconnectTask = nil
        queuedMessages.removeAll()
        reconnectAttempts = 0
        currentPath = nil
        currentAccessToken = nil
        currentGuestToken = nil
        currentHeartbeatEnabled = true
        closeSocket()
        status = .disconnected
    }

    private func closeSocket() {
        receiveTask?.cancel()
        receiveTask = nil
        heartbeatTask?.cancel()
        heartbeatTask = nil
        pongTimeoutTask?.cancel()
        pongTimeoutTask = nil
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
    }

    private func receiveLoop(_ socketTask: URLSessionWebSocketTask) async {
        while !Task.isCancelled {
            do {
                let message = try await socketTask.receive()
                switch message {
                case .string(let text):
                    if handleControlMessage(text) {
                        continue
                    }
                    reconnectAttempts = 0
                    messagesReceived += 1
                    lastMessage = text
                    onTextMessage?(text)
                case .data(let data):
                    reconnectAttempts = 0
                    messagesReceived += 1
                    lastMessage = String(data: data, encoding: .utf8) ?? "\(data.count) bytes"
                    if let text = String(data: data, encoding: .utf8) {
                        onTextMessage?(text)
                    }
                @unknown default:
                    messagesReceived += 1
                    lastMessage = "Unknown WebSocket message."
                }
            } catch {
                if !Task.isCancelled {
                    handleUnexpectedDisconnect(
                        from: socketTask,
                        errorMessage: error.localizedDescription
                    )
                }
                return
            }
        }
    }

    private func handleControlMessage(_ text: String) -> Bool {
        guard
            let data = text.data(using: .utf8),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            object["type"] as? String == "pong"
        else {
            return false
        }

        pongTimeoutTask?.cancel()
        pongTimeoutTask = nil
        reconnectAttempts = 0
        lastMessage = "Heartbeat acknowledged."
        return true
    }

    private func startHeartbeat(for socketTask: URLSessionWebSocketTask) {
        heartbeatTask?.cancel()
        heartbeatTask = Task { [weak self, weak socketTask] in
            guard let self, let socketTask else { return }

            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: 30_000_000_000)
                    try await socketTask.send(.string("{\"type\":\"ping\"}"))
                    await MainActor.run {
                        self.armPongTimeout(for: socketTask)
                    }
                } catch {
                    await MainActor.run {
                        if !Task.isCancelled {
                            self.handleUnexpectedDisconnect(
                                from: socketTask,
                                errorMessage: error.localizedDescription
                            )
                        }
                    }
                    return
                }
            }
        }
    }

    private func armPongTimeout(for socketTask: URLSessionWebSocketTask) {
        pongTimeoutTask?.cancel()
        pongTimeoutTask = Task { [weak self, weak socketTask] in
            do {
                try await Task.sleep(nanoseconds: 5_000_000_000)
            } catch {
                return
            }

            await MainActor.run {
                guard let self, let socketTask, self.task === socketTask else {
                    return
                }
                self.handleUnexpectedDisconnect(
                    from: socketTask,
                    errorMessage: "WebSocket heartbeat timed out."
                )
            }
        }
    }

    private func handleUnexpectedDisconnect(
        from socketTask: URLSessionWebSocketTask,
        errorMessage: String
    ) {
        guard task === socketTask else {
            return
        }

        closeSocket()

        guard !intentionalDisconnect else {
            status = .disconnected
            return
        }

        self.errorMessage = errorMessage
        scheduleReconnect()
    }

    private func scheduleReconnect() {
        guard
            reconnectAttempts < maxReconnectAttempts,
            let currentPath,
            currentAccessToken != nil || currentGuestToken != nil
        else {
            status = .failed
            if errorMessage == nil {
                errorMessage = "Connection lost. Refresh the game to reconnect."
            }
            return
        }

        status = .reconnecting
        reconnectTask?.cancel()

        let delay = min(pow(2.0, Double(reconnectAttempts)), 30)
        reconnectAttempts += 1

        reconnectTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            } catch {
                return
            }

            await MainActor.run {
                guard let self, !self.intentionalDisconnect else {
                    return
                }
                self.openSocket(
                    path: currentPath,
                    accessToken: self.currentAccessToken,
                    guestToken: self.currentGuestToken,
                    isReconnect: true
                )
            }
        }
    }

    private func flushQueuedMessages() {
        guard !queuedMessages.isEmpty else {
            return
        }

        let messages = queuedMessages
        queuedMessages.removeAll()

        for message in messages {
            send(text: message)
        }
    }

    private func makeURL(path: String, accessToken: String?, guestToken: String?) -> URL? {
        var components = URLComponents(
            url: AppConfig.websocketBaseURL,
            resolvingAgainstBaseURL: false
        )
        components?.path = path.hasPrefix("/") ? path : "/\(path)"
        var queryItems: [URLQueryItem] = []
        if let accessToken {
            queryItems.append(URLQueryItem(name: "token", value: accessToken))
        }
        if let guestToken {
            queryItems.append(URLQueryItem(name: "guest_token", value: guestToken))
        }
        components?.queryItems = queryItems.isEmpty ? nil : queryItems
        return components?.url
    }
}
