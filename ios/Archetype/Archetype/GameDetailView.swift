import SwiftUI

@MainActor
final class GameDetailViewModel: ObservableObject {
    @Published var gameJSON: JSONValue?
    @Published var isLoading = false
    @Published var errorMessage: String?

    var viewer: String {
        gameJSON?["viewer"]?.stringValue ?? "Unknown"
    }

    var phase: String {
        gameJSON?["phase"]?.stringValue ?? "Unknown"
    }

    var activeSide: String {
        gameJSON?["active"]?.stringValue ?? "Unknown"
    }

    var turn: String {
        if let value = gameJSON?["turn"]?.intValue {
            return String(value)
        }
        return "Unknown"
    }

    var cardsVisible: Int {
        gameJSON?["cards"]?.objectValue?.count ?? 0
    }

    func load(gameId: Int, using authStore: AuthStore) async {
        isLoading = true
        errorMessage = nil

        do {
            gameJSON = try await authStore.authenticatedGet("/gameplay/games/\(gameId)/")
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}

struct GameDetailView: View {
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var model = GameDetailViewModel()
    @StateObject private var socket = DrawTwoWebSocket()

    let gameId: Int

    var body: some View {
        List {
            summarySection
            socketSection
            rawStateSection
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Game \(gameId)")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await model.load(gameId: gameId, using: authStore) }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
            }
        }
        .task {
            await model.load(gameId: gameId, using: authStore)
            connectSocketIfPossible()
        }
        .onDisappear {
            socket.disconnect()
        }
    }

    private var summarySection: some View {
        Section("State") {
            LabeledContent("Viewer", value: model.viewer)
            LabeledContent("Phase", value: model.phase)
            LabeledContent("Active side", value: model.activeSide)
            LabeledContent("Turn", value: model.turn)
            LabeledContent("Visible cards", value: String(model.cardsVisible))

            if model.isLoading {
                ProgressView()
            }

            if let error = model.errorMessage {
                Text(error)
                    .font(.callout)
                    .foregroundStyle(.red)
            }
        }
    }

    private var socketSection: some View {
        Section("Live Game Socket") {
            Label(socket.status.rawValue, systemImage: "dot.radiowaves.left.and.right")
                .foregroundStyle(socket.status == .connected ? .green : .secondary)

            LabeledContent("Messages", value: String(socket.messagesReceived))

            Button {
                socket.sendPing()
            } label: {
                Label("Ping Game Socket", systemImage: "paperplane")
            }
            .disabled(socket.status != .connected)

            Text(socket.lastMessage)
                .font(.caption)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)

            if let error = socket.errorMessage {
                Text(error)
                    .font(.callout)
                    .foregroundStyle(.red)
            }
        }
    }

    private var rawStateSection: some View {
        Section("Raw State Preview") {
            Text(model.gameJSON?.prettyPrinted ?? "No game state loaded.")
                .font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
        }
    }

    private func connectSocketIfPossible() {
        guard let accessToken = authStore.currentAccessToken else {
            return
        }
        socket.connect(path: "/ws/game/\(gameId)/", accessToken: accessToken)
    }
}
