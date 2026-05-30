import Foundation

enum SocketStatus: String {
    case disconnected = "Disconnected"
    case connecting = "Connecting"
    case connected = "Connected"
    case failed = "Failed"
}

@MainActor
final class DrawTwoWebSocket: ObservableObject {
    @Published private(set) var status: SocketStatus = .disconnected
    @Published private(set) var messagesReceived = 0
    @Published private(set) var lastMessage = "No messages yet."
    @Published private(set) var errorMessage: String?

    private var task: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?

    func connect(path: String, accessToken: String) {
        disconnect()

        guard let url = makeURL(path: path, accessToken: accessToken) else {
            status = .failed
            errorMessage = "Could not build WebSocket URL."
            return
        }

        status = .connecting
        errorMessage = nil

        var request = URLRequest(url: url)
        request.setValue(AppConfig.backendBaseURL.absoluteString, forHTTPHeaderField: "Origin")
        request.setValue("Archetype-iOS/0.1", forHTTPHeaderField: "User-Agent")

        let socketTask = URLSession.shared.webSocketTask(with: request)
        task = socketTask
        socketTask.resume()
        status = .connected

        receiveTask = Task { [weak self, weak socketTask] in
            guard let self, let socketTask else { return }
            await self.receiveLoop(socketTask)
        }
    }

    func sendPing() {
        send(text: #"{"type":"ping"}"#)
    }

    func send(text: String) {
        guard let task else {
            errorMessage = "WebSocket is not connected."
            return
        }

        Task {
            do {
                try await task.send(.string(text))
            } catch {
                await MainActor.run {
                    self.status = .failed
                    self.errorMessage = error.localizedDescription
                }
            }
        }
    }

    func disconnect() {
        receiveTask?.cancel()
        receiveTask = nil
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        status = .disconnected
    }

    private func receiveLoop(_ socketTask: URLSessionWebSocketTask) async {
        while !Task.isCancelled {
            do {
                let message = try await socketTask.receive()
                switch message {
                case .string(let text):
                    messagesReceived += 1
                    lastMessage = text
                case .data(let data):
                    messagesReceived += 1
                    lastMessage = String(data: data, encoding: .utf8) ?? "\(data.count) bytes"
                @unknown default:
                    messagesReceived += 1
                    lastMessage = "Unknown WebSocket message."
                }
            } catch {
                if !Task.isCancelled {
                    status = .failed
                    errorMessage = error.localizedDescription
                }
                return
            }
        }
    }

    private func makeURL(path: String, accessToken: String) -> URL? {
        var components = URLComponents(
            url: AppConfig.websocketBaseURL,
            resolvingAgainstBaseURL: false
        )
        components?.path = path.hasPrefix("/") ? path : "/\(path)"
        components?.queryItems = [
            URLQueryItem(name: "token", value: accessToken)
        ]
        return components?.url
    }
}
