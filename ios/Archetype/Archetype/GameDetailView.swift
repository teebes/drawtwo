import SwiftUI

struct GameSideSnapshot {
    let side: String
    let label: String
    let heroId: String?
    let heroName: String
    let playerName: String?
    let description: String
    let health: Int?
    let maxHealth: Int?
    let heroArtURL: URL?
    let exhausted: Bool
    let heroPowerName: String?
    let heroPowerDescription: String?
    let heroPowerCost: Int
    let deckCount: Int
    let handCount: Int
    let boardCount: Int
    let energy: Int
    let energyPool: Int
}

struct BoardCardSnapshot: Identifiable, Equatable {
    let id: String
    let name: String
    let description: String
    let attack: Int
    let health: Int
    let cost: Int?
    let isSpell: Bool
    let exhausted: Bool
    let artURL: URL?
    let traits: [JSONValue]
    let traitIcon: String?

    var shortName: String {
        name.isEmpty ? "Unknown" : name
    }

    var isCreatureCard: Bool {
        !isSpell
    }

    var traitTypes: [String] {
        traits.compactMap { trait in
            trait["type"]?.stringValue ?? trait["slug"]?.stringValue
        }
    }

    var hasStealth: Bool {
        traitTypes.contains("stealth")
    }
}

struct GameUpdateSnapshot: Identifiable, Equatable {
    let id: String
    let value: JSONValue

    var type: String {
        value["type"]?.stringValue ?? "update"
    }

    var side: String {
        value["side"]?.stringValue ?? ""
    }

    var timestamp: String {
        value["timestamp"]?.stringValue ?? id
    }
}

enum GameUpdateEntitySnapshot {
    case card(BoardCardSnapshot)
    case hero(GameSideSnapshot)
}

struct EloRatingChangeSnapshot: Equatable {
    let winner: EloRatingPlayerChange
    let loser: EloRatingPlayerChange
}

struct EloRatingPlayerChange: Identifiable, Equatable {
    let id: String
    let displayName: String
    let oldRating: Int
    let newRating: Int
    let change: Int
}

enum BoardZone {
    case hand
    case ownBoard
    case opponentBoard
}

enum BoardCombatKind {
    case damage
    case heal
    case buff
    case remove
    case silence
    case summon

    var color: Color {
        switch self {
        case .damage, .remove:
            return ArchetypeTheme.red
        case .silence:
            return ArchetypeTheme.sky
        case .heal:
            return ArchetypeTheme.green
        case .buff, .summon:
            return ArchetypeTheme.violet
        }
    }

}

enum BoardCombatRole {
    case source(BoardCombatKind, Color)
    case target(BoardCombatKind, String?)

    var borderColor: Color {
        switch self {
        case .source(_, let color):
            return color
        case .target(let kind, _):
            return kind.color
        }
    }

    var valueText: String? {
        switch self {
        case .source:
            return nil
        case .target(_, let value):
            return value
        }
    }
}

struct BoardCombatMotion: Equatable {
    enum Kind {
        case lunge
        case hit
        case healSource
        case healTarget
        case spellTarget
    }

    let kind: Kind
    let unit: CGVector

    var offset: CGVector {
        CGVector(dx: unit.dx * magnitude, dy: unit.dy * magnitude)
    }

    private var magnitude: CGFloat {
        switch kind {
        case .lunge:
            return 14
        case .hit:
            return 10
        case .healSource:
            return 6
        case .healTarget:
            return 0
        case .spellTarget:
            return 8
        }
    }
}

struct BoardCombatMarker {
    let sourceType: String?
    let sourceId: String?
    let targetType: String?
    let targetId: String?
    let kind: BoardCombatKind
    let sourceColor: Color
    let valueText: String?
    var animationToken = UUID()
    var sourcePoint: CGPoint?
    var targetPoint: CGPoint?
    var isSpellSource = false
    var casterIsViewer = false

    init?(update: GameUpdateSnapshot, viewerSide: String) {
        sourceType = update.value["source_type"]?.stringValue
        sourceId = update.value["source_id"]?.stringValue
        targetType = update.value["target_type"]?.stringValue
        targetId = update.value["target_id"]?.stringValue
        sourceColor = update.side == viewerSide ? ArchetypeTheme.green : ArchetypeTheme.red

        switch update.type {
        case "update_damage":
            kind = .damage
            valueText = "-\(update.value["damage"]?.intValue ?? 0)"
        case "update_heal":
            kind = .heal
            valueText = "+\(update.value["amount"]?.intValue ?? 0)"
        case "update_buff":
            kind = .buff
            valueText = "+\(update.value["amount"]?.intValue ?? 0)"
        case "update_remove":
            kind = .remove
            valueText = nil
        case "update_silence":
            kind = .silence
            valueText = nil
        case "update_summon":
            kind = .summon
            valueText = nil
        default:
            return nil
        }
    }

    func role(forCardId id: String) -> BoardCombatRole? {
        if isBoardSource(sourceType), sourceId == id {
            return .source(kind, sourceColor)
        }
        if isBoardTarget(targetType), targetId == id {
            return .target(kind, valueText)
        }
        return nil
    }

    func role(forHeroId id: String?) -> BoardCombatRole? {
        guard let id else {
            return nil
        }
        if sourceType == "hero", sourceId == id {
            return .source(kind, sourceColor)
        }
        if targetType == "hero", targetId == id {
            return .target(kind, valueText)
        }
        return nil
    }

    func motion(forCardId id: String) -> BoardCombatMotion? {
        if isBoardSource(sourceType), sourceId == id {
            return sourceMotion
        }
        if isBoardTarget(targetType), targetId == id {
            return targetMotion
        }
        return nil
    }

    func motion(forHeroId id: String?) -> BoardCombatMotion? {
        guard let id else {
            return nil
        }
        if sourceType == "hero", sourceId == id {
            return sourceMotion
        }
        if targetType == "hero", targetId == id {
            return targetMotion
        }
        return nil
    }

    private var sourceMotion: BoardCombatMotion? {
        guard sourceId != targetId else {
            return nil
        }

        switch kind {
        case .damage:
            return BoardCombatMotion(kind: .lunge, unit: unitVector(pointingAtTarget: true))
        case .heal:
            return BoardCombatMotion(kind: .healSource, unit: unitVector(pointingAtTarget: true))
        default:
            return nil
        }
    }

    private var targetMotion: BoardCombatMotion? {
        switch kind {
        case .damage:
            return BoardCombatMotion(
                kind: isSpellSource ? .spellTarget : .hit,
                unit: unitVector(pointingAtTarget: false)
            )
        case .heal:
            return BoardCombatMotion(kind: .healTarget, unit: .zero)
        default:
            return nil
        }
    }

    private func unitVector(pointingAtTarget: Bool) -> CGVector {
        guard let sourcePoint, let targetPoint else {
            // Spell sources sit near the caster's hand, so push along the
            // vertical axis toward or away from the caster's side.
            let towardCaster: CGFloat = casterIsViewer ? 1 : -1
            return CGVector(dx: 0, dy: pointingAtTarget ? -towardCaster : towardCaster)
        }

        let dx = targetPoint.x - sourcePoint.x
        let dy = targetPoint.y - sourcePoint.y
        let distance = hypot(dx, dy)
        guard distance >= 1 else {
            return .zero
        }

        let direction: CGFloat = pointingAtTarget ? 1 : -1
        return CGVector(dx: (dx / distance) * direction, dy: (dy / distance) * direction)
    }

    private func isBoardSource(_ type: String?) -> Bool {
        type == "creature" || type == "board"
    }

    private func isBoardTarget(_ type: String?) -> Bool {
        type == "creature" || type == "card" || type == "board"
    }
}

enum BoardCombatAnimationKind {
    case damage
    case spellDamage
    case heal

    var accent: Color {
        switch self {
        case .damage:
            return ArchetypeTheme.gold2
        case .spellDamage:
            return ArchetypeTheme.sky
        case .heal:
            return ArchetypeTheme.green
        }
    }

    var impact: Color {
        switch self {
        case .damage, .spellDamage:
            return ArchetypeTheme.red
        case .heal:
            return ArchetypeTheme.green
        }
    }

    var valuePrefix: String {
        switch self {
        case .damage, .spellDamage:
            return "-"
        case .heal:
            return "+"
        }
    }
}

struct BoardTransientCombat {
    let id: String
    let kind: BoardCombatAnimationKind
    let source: CGPoint
    let target: CGPoint
    let value: Int
    let isRetaliation: Bool

    var accent: Color {
        isRetaliation ? ArchetypeTheme.red : kind.accent
    }

    var trailTip: Color {
        isRetaliation ? ArchetypeTheme.gold2 : kind.impact
    }
}

struct BoardValueBurst: Identifiable, Equatable {
    let id: String
    let kind: BoardCombatAnimationKind
    let value: Int
    let point: CGPoint

    var text: String {
        "\(kind.valuePrefix)\(value)"
    }
}

struct BoardPlayedSpellCard: Identifiable, Equatable {
    let id: String
    let side: String
    let card: BoardCardSnapshot
    let isLeaving: Bool
}

struct BoardEntityAnchorPreferenceKey: PreferenceKey {
    static var defaultValue: [String: Anchor<CGRect>] = [:]

    static func reduce(
        value: inout [String: Anchor<CGRect>],
        nextValue: () -> [String: Anchor<CGRect>]
    ) {
        value.merge(nextValue(), uniquingKeysWith: { _, new in new })
    }
}

enum TargetAllowed {
    case creature
    case hero
    case both

    var allowsCreature: Bool {
        self == .creature || self == .both
    }

    var allowsHero: Bool {
        self == .hero || self == .both
    }
}

enum TargetScope {
    case enemy
    case friendly
    case any
}

struct TargetRules {
    let requiresTarget: Bool
    let allowed: TargetAllowed
    let scope: TargetScope
    let bypassTaunt: Bool
}

struct GameTargetOption: Identifiable {
    enum Kind {
        case creature
        case hero
    }

    let id: String
    let side: String
    let kind: Kind
    let title: String
    let subtitle: String
    let card: BoardCardSnapshot?
    let hero: GameSideSnapshot?
    let enabled: Bool
}

enum PendingGameCommand {
    case playCard(cardId: String, position: Int)
    case attack(cardId: String)
    case heroPower(heroId: String)
}

struct GameTargetingContext: Identifiable {
    let id = UUID()
    let title: String
    let sourceName: String
    let sourceCard: BoardCardSnapshot?
    let allowed: TargetAllowed
    let scope: TargetScope
    let bypassTaunt: Bool
    let unavailableReason: String?
    let command: PendingGameCommand
}

struct GamePlacementContext: Identifiable {
    let id = UUID()
    let card: BoardCardSnapshot
    let boardCards: [BoardCardSnapshot]

    var boardCount: Int {
        boardCards.count
    }
}

enum GameEntityKind {
    case handCard
    case ownCreature
    case opponentCreature
    case ownHero
    case opponentHero
}

struct GameEntityDetailContext: Identifiable {
    let id = UUID()
    let kind: GameEntityKind
    let card: BoardCardSnapshot?
    let hero: GameSideSnapshot?
}

enum GameOverlay: Identifiable {
    case entity(GameEntityDetailContext)
    case placement(GamePlacementContext)
    case targeting(GameTargetingContext)
    case updates
    case howToPlay
    case menu

    var id: String {
        switch self {
        case .entity(let context):
            return "entity-\(context.id)"
        case .placement(let context):
            return "placement-\(context.id)"
        case .targeting(let context):
            return "targeting-\(context.id)"
        case .updates:
            return "updates"
        case .howToPlay:
            return "how-to-play"
        case .menu:
            return "menu"
        }
    }

    var captureScreenName: String {
        switch self {
        case .entity(let context):
            switch context.kind {
            case .handCard:
                return context.card?.isCreatureCard == true ? "game-hand-creature" : "game-hand-card"
            case .ownCreature:
                return "game-own-creature"
            case .opponentCreature:
                return "game-opponent-creature"
            case .ownHero:
                return "game-own-hero"
            case .opponentHero:
                return "game-opponent-hero"
            }
        case .placement:
            return "game-placement"
        case .targeting(let context):
            switch context.command {
            case .attack:
                return "game-targeting-attack"
            case .playCard:
                return context.sourceCard?.isSpell == true ? "game-targeting-spell" : "game-placement"
            case .heroPower:
                return "game-targeting-hero-power"
            }
        case .updates:
            return "game-updates"
        case .howToPlay:
            return "game-how-to-play"
        case .menu:
            return "game-menu"
        }
    }
}

@MainActor
final class GameDetailViewModel: ObservableObject {
    @Published var gameJSON: JSONValue?
    @Published var updates: [GameUpdateSnapshot] = []
    @Published private(set) var liveUpdateBatch: [GameUpdateSnapshot] = []
    @Published private(set) var liveUpdateBatchId = 0
    @Published private(set) var liveGameOverVersion = 0
    @Published var isLoading = false
    @Published var isRematchLoading = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?
    @Published var activeGames: [GameSummary] = []

    private let api = APIClient.shared
    private var hasReceivedInitialSocketSnapshot = false

    private static let displayUpdateTypes: Set<String> = [
        "update_draw_card",
        "update_play_card",
        "update_end_turn",
        "update_damage",
        "update_heal",
        "update_buff",
        "update_summon",
        "update_remove",
        "update_silence",
    ]
    private static let socketPreservedKeys = [
        "viewer",
        "is_vs_ai",
        "game_type",
        "ladder_type",
        "elo_change",
    ]

    var viewer: String {
        gameJSON?["viewer"]?.stringValue ?? "Unknown"
    }

    var viewerSide: String {
        viewer == "side_b" ? "side_b" : "side_a"
    }

    var opponentSide: String {
        viewerSide == "side_a" ? "side_b" : "side_a"
    }

    var phase: String {
        gameJSON?["phase"]?.stringValue ?? "Unknown"
    }

    var activeSide: String {
        gameJSON?["active"]?.stringValue ?? "Unknown"
    }

    var isPlayerTurn: Bool {
        activeSide == viewerSide && phase == "main"
    }

    var isPlayerActionRequired: Bool {
        guard winner == "none" else {
            return false
        }
        if phase == "mulligan" {
            return !ownMulliganDone
        }
        return isPlayerTurn
    }

    var turn: String {
        if let value = gameJSON?["turn"]?.intValue {
            return String(value)
        }
        return "Unknown"
    }

    var winner: String {
        gameJSON?["winner"]?.stringValue ?? "none"
    }

    var isMulliganPhase: Bool {
        phase == "mulligan"
    }

    var ownMulliganDone: Bool {
        gameJSON?["mulligan_done"]?[viewerSide]?.boolValue ?? false
    }

    var timePerTurn: Int {
        gameJSON?["time_per_turn"]?.intValue ?? 0
    }

    var turnExpires: Date? {
        guard let string = gameJSON?["turn_expires"]?.stringValue else {
            return nil
        }
        return ISO8601DateFormatter.drawTwoDate(from: string)
    }

    var gameType: String {
        gameJSON?["game_type"]?.stringValue ?? ""
    }

    var ladderType: LadderType? {
        guard let rawValue = gameJSON?["ladder_type"]?.stringValue else {
            return nil
        }
        return LadderType(rawValue: rawValue)
    }

    var canRequestRematch: Bool {
        winner != "none" && gameType == "friendly"
    }

    var canExtendTime: Bool {
        winner == "none" && gameType == "ranked"
    }

    var eloChange: EloRatingChangeSnapshot? {
        guard let value = gameJSON?["elo_change"] else {
            return nil
        }

        guard
            let winner = ratingPlayerChange(from: value["winner"], id: "winner"),
            let loser = ratingPlayerChange(from: value["loser"], id: "loser")
        else {
            return nil
        }

        return EloRatingChangeSnapshot(winner: winner, loser: loser)
    }

    var currentGameOverTitle: String {
        guard winner != "none" else {
            return ""
        }
        return winner == viewerSide ? "Victory!" : "Defeat!"
    }

    var displayUpdates: [GameUpdateSnapshot] {
        updates.filter { Self.displayUpdateTypes.contains($0.type) }
    }

    var latestDisplayUpdateText: String {
        guard let update = displayUpdates.last else {
            return "No updates yet"
        }
        return updateText(update)
    }

    var latestDisplayUpdateCompactText: String {
        guard let update = displayUpdates.last else {
            return "No updates yet"
        }
        return compactUpdateText(update)
    }

    var hasNoAvailableActions: Bool {
        guard isPlayerTurn, winner == "none" else {
            return false
        }

        let canPlayAnyCard = handCards(for: viewerSide).contains { isHandCardPlayable($0) }
        if canPlayAnyCard {
            return false
        }

        let canAttackWithAnyCreature = boardCards(for: viewerSide).contains {
            attackUnavailableReason($0) == nil
        }
        if canAttackWithAnyCreature {
            return false
        }

        return heroPowerUnavailableReason(for: viewerSide) != nil
    }

    var cardsVisible: Int {
        gameJSON?["cards"]?.objectValue?.count ?? 0
    }

    func nextGame(currentGameId: Int) -> GameSummary? {
        let availableGames = activeGames.filter { $0.isUserTurn && $0.id != currentGameId }

        if gameType == "ranked", ladderType == .rapid {
            return nil
        }

        if gameType == "pve" {
            return availableGames.first(where: Self.isRapidRankedGame)
        }

        return availableGames.first(where: Self.isRapidRankedGame)
            ?? availableGames.first(where: Self.isPvpGame)
            ?? availableGames.first { $0.type == "pve" }
    }

    private static func isRapidRankedGame(_ game: GameSummary) -> Bool {
        game.type == "ranked" && game.ladderType == .rapid
    }

    private static func isPvpGame(_ game: GameSummary) -> Bool {
        game.type == "ranked" || game.type == "friendly"
    }

    func resetForGameLoad() {
        gameJSON = nil
        updates = []
        liveUpdateBatch = []
        liveUpdateBatchId = 0
        liveGameOverVersion = 0
        hasReceivedInitialSocketSnapshot = false
        errorMessage = nil
        statusMessage = nil
        isLoading = false
        isRematchLoading = false
    }

    func prepareForSocketSnapshotSync() {
        hasReceivedInitialSocketSnapshot = false
        liveUpdateBatch = []
    }

    func load(gameId: Int, using authStore: AuthStore, guestAccessToken: String? = nil) async {
        isLoading = true
        errorMessage = nil

        do {
            if let guestAccessToken {
                let response: JSONValue = try await api.get(
                    "/gameplay/games/\(gameId)/",
                    queryItems: guestQueryItems(guestAccessToken)
                )
                gameJSON = response
                prefetchArt(in: response)
            } else {
                let response: JSONValue = try await authStore.authenticatedGet("/gameplay/games/\(gameId)/")
                gameJSON = response
                prefetchArt(in: response)
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func loadActiveGames(using authStore: AuthStore, guestAccessToken: String? = nil) async {
        guard guestAccessToken == nil else {
            activeGames = []
            return
        }

        do {
            let response: GameListResponse = try await authStore.authenticatedGet(
                "/titles/\(AppConfig.titleSlug)/games/"
            )
            activeGames = response.games
        } catch {
            activeGames = []
        }
    }

    func fetchEloChangeIfNeeded(
        gameId: Int,
        using authStore: AuthStore,
        guestAccessToken: String? = nil
    ) async {
        guard winner != "none", eloChange == nil else {
            return
        }
        guard guestAccessToken == nil else {
            return
        }

        do {
            let response: JSONValue = try await authStore.authenticatedGet("/gameplay/games/\(gameId)/")
            guard let eloChange = response["elo_change"], eloChange.objectValue != nil else {
                return
            }
            mergeEloChange(eloChange)
        } catch {
            // Best-effort parity with the web overlay: keep game-over flow usable.
        }
    }

    @discardableResult
    func requestRematch(gameId: Int, using authStore: AuthStore) async -> Bool {
        guard canRequestRematch else {
            errorMessage = "Rematch is only available after completed friendly games."
            return false
        }

        isRematchLoading = true
        errorMessage = nil
        statusMessage = nil

        do {
            let _: RematchResponse = try await authStore.authenticatedPost(
                "/gameplay/games/\(gameId)/rematch/",
                body: EmptyBody()
            )
            statusMessage = "Rematch challenge sent."
            isRematchLoading = false
            return true
        } catch {
            errorMessage = error.localizedDescription
            isRematchLoading = false
            return false
        }
    }

    func applySocketText(_ text: String) {
        guard let data = text.data(using: .utf8) else {
            return
        }

        do {
            let payload = try JSONDecoder().decode(JSONValue.self, from: data)
            let state = payload["state"]
            let hasStatePayload = state?.objectValue != nil
            let shouldPublishLiveBatch = hasReceivedInitialSocketSnapshot
            if hasStatePayload {
                hasReceivedInitialSocketSnapshot = true
            }
            let previousWinner = winner

            guard
                let state,
                state.objectValue != nil
            else {
                appendErrors(from: payload)
                appendUpdates(from: payload, publishLiveBatch: shouldPublishLiveBatch)
                if shouldPublishLiveBatch, payloadIncludesGameOverUpdate(payload) {
                    liveGameOverVersion += 1
                }
                return
            }
            if var stateObject = state.objectValue {
                let existingObject = gameJSON?.objectValue ?? [:]
                for key in Self.socketPreservedKeys where stateObject[key] == nil {
                    stateObject[key] = existingObject[key]
                }
                let mergedState = JSONValue.object(stateObject)
                gameJSON = mergedState
                prefetchArt(in: mergedState)
            }
            appendErrors(from: payload)
            appendUpdates(from: payload, publishLiveBatch: shouldPublishLiveBatch)
            if shouldPublishLiveBatch, previousWinner == "none", winner != "none" {
                liveGameOverVersion += 1
            }
        } catch {
            errorMessage = "Could not parse live game update: \(error.localizedDescription)"
        }
    }

    func snapshot(for side: String, label: String) -> GameSideSnapshot {
        let hero = gameJSON?["heroes"]?[side]
        let pool = intValue(at: "mana_pool", side: side)
        let used = intValue(at: "mana_used", side: side)

        return GameSideSnapshot(
            side: side,
            label: label,
            heroId: hero?["hero_id"]?.stringValue,
            heroName: hero?["name"]?.stringValue ?? hero?["player_name"]?.stringValue ?? side,
            playerName: hero?["player_name"]?.stringValue,
            description: hero?["description"]?.stringValue ?? "",
            health: hero?["health"]?.intValue,
            maxHealth: hero?["health_max"]?.intValue,
            heroArtURL: url(
                from: hero?["art_url"]?.stringValue
                    ?? AppConfig.heroArtURL(slug: hero?["template_slug"]?.stringValue)
            ),
            exhausted: hero?["exhausted"]?.boolValue ?? false,
            heroPowerName: hero?["hero_power"]?["name"]?.stringValue,
            heroPowerDescription: hero?["hero_power"]?["description"]?.stringValue,
            heroPowerCost: max(hero?["hero_power"]?["cost"]?.intValue ?? 0, 0),
            deckCount: gameJSON?["decks"]?[side]?.arrayValue?.count ?? 0,
            handCount: gameJSON?["hands"]?[side]?.arrayValue?.count ?? 0,
            boardCount: gameJSON?["board"]?[side]?.arrayValue?.count ?? 0,
            energy: max(pool - used, 0),
            energyPool: pool
        )
    }

    func availableEnergy(for side: String) -> Int {
        let pool = intValue(at: "mana_pool", side: side)
        let used = intValue(at: "mana_used", side: side)
        return max(pool - used, 0)
    }

    func boardCards(for side: String) -> [BoardCardSnapshot] {
        let ids = gameJSON?["board"]?[side]?.arrayValue?.compactMap(\.stringValue) ?? []
        return ids.compactMap { id in
            cardSnapshot(from: gameJSON?["creatures"]?[id], id: id, fallbackCost: nil)
        }
    }

    func handCards(for side: String) -> [BoardCardSnapshot] {
        let ids = gameJSON?["hands"]?[side]?.arrayValue?.compactMap(\.stringValue) ?? []
        return ids.compactMap { id in
            cardSnapshot(from: gameJSON?["cards"]?[id], id: id, fallbackCost: gameJSON?["cards"]?[id]?["cost"]?.intValue)
        }
    }

    func mulliganCards() -> [BoardCardSnapshot] {
        let optionIds = gameJSON?["mulligan_options"]?[viewerSide]?.arrayValue?.compactMap(\.stringValue) ?? []
        let ids = optionIds.isEmpty
            ? (gameJSON?["hands"]?[viewerSide]?.arrayValue?.compactMap(\.stringValue) ?? [])
            : optionIds
        return ids.compactMap { id in
            cardSnapshot(from: gameJSON?["cards"]?[id], id: id, fallbackCost: gameJSON?["cards"]?[id]?["cost"]?.intValue)
        }
    }

    func isHandCardPlayable(_ card: BoardCardSnapshot) -> Bool {
        guard let cost = card.cost else {
            return false
        }
        return isPlayerTurn && winner == "none" && cost <= availableEnergy(for: viewerSide)
    }

    func cardPlayUnavailableReason(_ card: BoardCardSnapshot) -> String? {
        guard winner == "none" else {
            return "Game is already over."
        }
        guard isPlayerTurn else {
            return "You can only play cards during your main phase."
        }
        guard let cost = card.cost else {
            return "This card cannot be played from here."
        }
        let energy = availableEnergy(for: viewerSide)
        guard cost <= energy else {
            return "Not enough energy. Need \(cost), have \(energy)."
        }
        return nil
    }

    func attackUnavailableReason(_ creature: BoardCardSnapshot) -> String? {
        guard winner == "none" else {
            return "Game is already over."
        }
        guard isPlayerTurn else {
            return "You can only attack during your main phase."
        }
        guard !creature.exhausted else {
            return "Creature is exhausted."
        }
        guard creature.attack > 0 else {
            return "Creature has no attack."
        }
        return nil
    }

    func heroPowerUnavailableReason(for side: String) -> String? {
        let hero = snapshot(for: side, label: side == viewerSide ? "You" : "Opponent")
        guard winner == "none" else {
            return "Game is already over."
        }
        guard side == viewerSide, isPlayerTurn else {
            return "You can only use your hero power during your main phase."
        }
        guard let _ = hero.heroId else {
            return "Hero power is unavailable."
        }
        guard !hero.exhausted else {
            return "Hero is exhausted."
        }
        let energy = availableEnergy(for: viewerSide)
        guard hero.heroPowerCost <= energy else {
            return "Not enough energy. Need \(hero.heroPowerCost), have \(energy)."
        }
        return nil
    }

    func targetRules(for card: BoardCardSnapshot, battlecryOnly: Bool = false) -> TargetRules {
        let rules = Self.targetRules(from: card.traits, battlecryOnly: battlecryOnly)
        if card.isSpell && !battlecryOnly {
            return TargetRules(
                requiresTarget: rules.requiresTarget,
                allowed: rules.allowed,
                scope: rules.scope,
                bypassTaunt: true
            )
        }
        return rules
    }

    func heroTargetRules(for side: String) -> TargetRules {
        let actions = gameJSON?["heroes"]?[side]?["hero_power"]?["actions"]?.arrayValue ?? []
        let traitLike = JSONValue.object([
            "type": .string("hero_power"),
            "actions": .array(actions),
        ])
        return Self.targetRules(from: [traitLike], battlecryOnly: false)
    }

    func heroPowerRequiresTarget(for side: String) -> Bool {
        heroTargetRules(for: side).requiresTarget
    }

    func timeLeftString(now: Date) -> String? {
        guard timePerTurn > 0, let turnExpires else {
            return nil
        }
        let seconds = max(0, Int(turnExpires.timeIntervalSince(now)))
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let remainingSeconds = seconds % 60

        if hours > 0 {
            return "\(hours):\(String(format: "%02d", minutes)):\(String(format: "%02d", remainingSeconds))"
        }
        return "\(minutes):\(String(format: "%02d", remainingSeconds))"
    }

    func updateText(_ update: GameUpdateSnapshot, hideSource: Bool = false) -> String {
        let sideName: String
        if hideSource {
            sideName = ""
        } else if update.side == viewerSide {
            sideName = "You: "
        } else {
            sideName = "\(snapshot(for: update.side, label: "Opponent").heroName): "
        }

        switch update.type {
        case "update_draw_card":
            let cardName = entityName(
                type: "card",
                id: update.value["card_id"]?.stringValue,
                side: update.side
            ) ?? "a card"
            return "\(sideName)Draw \(cardName)"
        case "update_play_card":
            let cardName = entityName(
                type: "card",
                id: update.value["card_id"]?.stringValue ?? update.value["source_id"]?.stringValue,
                side: update.side
            ) ?? "a card"
            return "\(sideName)Play \(cardName)"
        case "update_end_turn":
            return "\(sideName)End Turn"
        case "update_damage":
            let source = entityName(
                type: update.value["source_type"]?.stringValue,
                id: update.value["source_id"]?.stringValue,
                side: update.side
            ) ?? "a unit"
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a target"
            let damage = update.value["damage"]?.intValue ?? 0
            return "\(sideName)\(source) -> \(target) -\(damage)"
        case "update_heal":
            let source = entityName(
                type: update.value["source_type"]?.stringValue,
                id: update.value["source_id"]?.stringValue,
                side: update.side
            ) ?? "a unit"
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a target"
            let amount = update.value["amount"]?.intValue ?? 0
            return "\(sideName)\(source) heals \(target) +\(amount)"
        case "update_buff":
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a target"
            let attribute = update.value["attribute"]?.stringValue ?? "stat"
            let amount = update.value["amount"]?.intValue ?? 0
            return "\(sideName)\(target) gains +\(amount) \(attribute)"
        case "update_summon":
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a creature"
            return "\(sideName)Summon \(target)"
        case "update_remove":
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a creature"
            return "\(sideName)Remove \(target)"
        case "update_silence":
            let target = entityName(
                type: update.value["target_type"]?.stringValue,
                id: update.value["target_id"]?.stringValue,
                side: update.side
            ) ?? "a creature"
            return "\(sideName)Silence \(target)"
        default:
            return sideName + update.type.replacingOccurrences(of: "update_", with: "").displayNameFromSlug
        }
    }

    func compactUpdateText(_ update: GameUpdateSnapshot) -> String {
        switch update.type {
        case "update_draw_card":
            return update.side == viewerSide ? "Draw" : "Draws a card"
        case "update_play_card":
            return "Play"
        default:
            return updateText(update)
        }
    }

    func updateCardSnapshot(_ update: GameUpdateSnapshot) -> BoardCardSnapshot? {
        let cardId: String?
        switch update.type {
        case "update_draw_card":
            cardId = update.value["card_id"]?.stringValue
        case "update_play_card":
            cardId = update.value["card_id"]?.stringValue
                ?? update.value["source_id"]?.stringValue
        default:
            cardId = nil
        }

        guard let cardId else {
            return nil
        }
        return cardSnapshot(
            from: gameJSON?["cards"]?[cardId],
            id: cardId,
            fallbackCost: gameJSON?["cards"]?[cardId]?["cost"]?.intValue
        )
    }

    func updateEntitySnapshot(
        type: String?,
        id: String?,
        side: String
    ) -> GameUpdateEntitySnapshot? {
        guard let id else {
            return nil
        }

        if type == "hero" {
            for heroSide in ["side_a", "side_b"] {
                let hero = gameJSON?["heroes"]?[heroSide]
                if hero?["hero_id"]?.stringValue == id || heroSide == id {
                    return .hero(snapshot(for: heroSide, label: heroSide))
                }
            }
            return .hero(snapshot(for: side, label: side))
        }

        if type == "creature" || type == "board" {
            if let card = cardSnapshot(from: gameJSON?["creatures"]?[id], id: id, fallbackCost: nil) {
                return .card(card)
            }
        }

        if type == "card" || type == nil {
            if let card = cardSnapshot(
                from: gameJSON?["cards"]?[id],
                id: id,
                fallbackCost: gameJSON?["cards"]?[id]?["cost"]?.intValue
            ) {
                return .card(card)
            }
            if let card = cardSnapshot(from: gameJSON?["creatures"]?[id], id: id, fallbackCost: nil) {
                return .card(card)
            }
        }

        return nil
    }

    func targetOptions(for context: GameTargetingContext) -> [GameTargetOption] {
        var options: [GameTargetOption] = []

        func includeSide(_ side: String, label: String, isEnemy: Bool) {
            let sideSnapshot = snapshot(for: side, label: label)
            let board = boardCards(for: side)
            let enemyBoard = isEnemy ? board : boardCards(for: opponentSide)
            let hasTaunt = enemyBoard.contains { $0.hasTrait("taunt") }
            let restrictForTaunt = isEnemy && hasTaunt && !context.bypassTaunt

            if context.allowed.allowsHero {
                options.append(
                    GameTargetOption(
                        id: "hero-\(sideSnapshot.heroId ?? side)",
                        side: side,
                        kind: .hero,
                        title: sideSnapshot.heroName,
                        subtitle: "\(sideSnapshot.health.map(String.init) ?? "-") HP",
                        card: nil,
                        hero: sideSnapshot,
                        enabled: !restrictForTaunt
                    )
                )
            }

            if context.allowed.allowsCreature {
                options += board.map { card in
                    let blockedByStealth = isEnemy && card.hasTrait("stealth")
                    let blockedByTaunt = restrictForTaunt && !card.hasTrait("taunt")
                    return GameTargetOption(
                        id: "creature-\(card.id)",
                        side: side,
                        kind: .creature,
                        title: card.shortName,
                        subtitle: "\(card.attack)/\(card.health)",
                        card: card,
                        hero: nil,
                        enabled: !blockedByStealth && !blockedByTaunt
                    )
                }
            }
        }

        switch context.scope {
        case .enemy:
            includeSide(opponentSide, label: "Opponent", isEnemy: true)
        case .friendly:
            includeSide(viewerSide, label: "You", isEnemy: false)
        case .any:
            includeSide(opponentSide, label: "Opponent", isEnemy: true)
            includeSide(viewerSide, label: "You", isEnemy: false)
        }

        return options
    }

    func commandTargetPayload(
        option: GameTargetOption,
        command: PendingGameCommand
    ) -> (targetType: String, targetId: String)? {
        switch (option.kind, command) {
        case (.hero, _):
            guard let targetId = option.hero?.heroId else {
                return nil
            }
            return ("hero", targetId)
        case (.creature, .attack):
            return ("creature", option.id.replacingOccurrences(of: "creature-", with: ""))
        case (.creature, .playCard), (.creature, .heroPower):
            return ("card", option.id.replacingOccurrences(of: "creature-", with: ""))
        }
    }

    private func cardSnapshot(from value: JSONValue?, id: String, fallbackCost: Int?) -> BoardCardSnapshot? {
        guard let value else {
            return nil
        }

        let traits = value["traits"]?.arrayValue ?? []
        let traitTypes = traits.compactMap { trait -> String? in
            trait["type"]?.stringValue ?? trait["slug"]?.stringValue
        }
        let cardType = value["card_type"]?.stringValue ?? ""
        let attack = value["attack"]?.intValue ?? 0
        let health = value["health"]?.intValue ?? 0
        let linkedCardId = value["card_id"]?.stringValue
        let templateSlug = value["template_slug"]?.stringValue
            ?? linkedCardId.flatMap { gameJSON?["cards"]?[$0]?["template_slug"]?.stringValue }
        let artUrl = value["art_url"]?.stringValue
            ?? templateSlug.flatMap { AppConfig.cardArtURL(slug: $0) }

        return BoardCardSnapshot(
            id: id,
            name: value["name"]?.stringValue ?? templateSlug?.displayNameFromSlug ?? "Unknown",
            description: value["description"]?.stringValue ?? "",
            attack: attack,
            health: health,
            cost: value["cost"]?.intValue ?? fallbackCost,
            isSpell: cardType == "spell" || (attack == 0 && health == 0),
            exhausted: value["exhausted"]?.boolValue ?? false,
            artURL: url(from: artUrl),
            traits: traits,
            traitIcon: Self.traitIcon(for: traitTypes)
        )
    }

    private func intValue(at key: String, side: String) -> Int {
        gameJSON?[key]?[side]?.intValue ?? 0
    }

    private func ratingPlayerChange(from value: JSONValue?, id: String) -> EloRatingPlayerChange? {
        guard let value else {
            return nil
        }

        return EloRatingPlayerChange(
            id: id,
            displayName: value["display_name"]?.stringValue ?? id.capitalized,
            oldRating: value["old_rating"]?.intValue ?? 0,
            newRating: value["new_rating"]?.intValue ?? 0,
            change: value["change"]?.intValue ?? 0
        )
    }

    private func mergeEloChange(_ eloChange: JSONValue) {
        guard var object = gameJSON?.objectValue else {
            return
        }

        object["elo_change"] = eloChange
        gameJSON = .object(object)
    }

    private func url(from string: String?) -> URL? {
        guard let string, !string.isEmpty else {
            return nil
        }
        return URL(string: string)
    }

    private func prefetchArt(in state: JSONValue?) {
        guard let state else {
            return
        }

        var urls: [URL] = []

        func append(_ string: String?) {
            if let url = url(from: string) {
                urls.append(url)
            }
        }

        if let heroes = state["heroes"]?.objectValue {
            for hero in heroes.values {
                append(resolvedHeroArtURL(from: hero))
            }
        }

        if let cards = state["cards"]?.objectValue {
            for card in cards.values {
                append(resolvedCardArtURL(from: card, state: state))
            }
        }

        if let creatures = state["creatures"]?.objectValue {
            for creature in creatures.values {
                append(resolvedCardArtURL(from: creature, state: state))
            }
        }

        RemoteImageCache.shared.prefetch(urls)
    }

    private func resolvedHeroArtURL(from value: JSONValue) -> String? {
        if let artURL = value["art_url"]?.stringValue, !artURL.isEmpty {
            return artURL
        }

        return AppConfig.heroArtURL(slug: value["template_slug"]?.stringValue)
    }

    private func resolvedCardArtURL(from value: JSONValue, state: JSONValue) -> String? {
        if let artURL = value["art_url"]?.stringValue, !artURL.isEmpty {
            return artURL
        }

        if let slug = value["template_slug"]?.stringValue ?? value["slug"]?.stringValue {
            return AppConfig.cardArtURL(slug: slug)
        }

        if let linkedCardId = value["card_id"]?.stringValue,
           let linkedCard = state["cards"]?[linkedCardId],
           let linkedSlug = linkedCard["template_slug"]?.stringValue ?? linkedCard["slug"]?.stringValue {
            return AppConfig.cardArtURL(slug: linkedSlug)
        }

        return nil
    }

    private static func traitIcon(for traitTypes: [String]) -> String? {
        let priority: [(String, String)] = [
            ("stealth", "👁️"),
            ("taunt", "🛡️"),
            ("deathrattle", "💀"),
            ("battlecry", "📣"),
            ("ranged", "🏹"),
            ("charge", "⚔️"),
            ("unique", "⭐"),
        ]

        return priority.first { traitTypes.contains($0.0) }?.1
    }

    private static func targetRules(from traits: [JSONValue], battlecryOnly: Bool) -> TargetRules {
        var requiresTarget = false
        var allowed = Set<String>()
        var scope: TargetScope = .enemy
        var bypassTaunt = false

        for trait in traits {
            let type = trait["type"]?.stringValue ?? trait["slug"]?.stringValue ?? ""
            if battlecryOnly && type != "battlecry" {
                continue
            }

            for action in trait["actions"]?.arrayValue ?? [] {
                let actionName = action["action"]?.stringValue ?? ""
                let target = action["target"]?.stringValue ?? ""
                let actionScope = action["scope"]?.stringValue ?? "single"

                if actionName == "damage", action["damage_type"]?.stringValue == "spell" {
                    bypassTaunt = true
                }

                switch actionName {
                case "damage":
                    if target == "creature" || target == "enemy" || target == "friendly" {
                        allowed.insert("creature")
                    }
                    if target == "hero" || target == "enemy" || target == "friendly" {
                        allowed.insert("hero")
                    }
                    scope = (target == "friendly" || target == "self") ? .friendly : .enemy
                case "heal":
                    if target == "creature" || target == "friendly" {
                        allowed.insert("creature")
                    }
                    if target == "hero" || target == "friendly" {
                        allowed.insert("hero")
                    }
                    scope = .friendly
                case "remove":
                    allowed.insert("creature")
                    scope = .enemy
                case "silence":
                    allowed.insert("creature")
                    scope = .enemy
                case "buff":
                    if target == "creature" || target == "friendly" {
                        allowed.insert("creature")
                    }
                    if target == "hero" || target == "friendly" {
                        allowed.insert("hero")
                    }
                    scope = .friendly
                default:
                    break
                }

                let targetingAction = ["damage", "heal", "remove", "silence", "buff"].contains(actionName)
                if targetingAction && actionScope != "all" && !(actionName == "buff" && target == "hero") {
                    requiresTarget = true
                }
            }
        }

        let targetAllowed: TargetAllowed
        if allowed.contains("creature") && allowed.contains("hero") {
            targetAllowed = .both
        } else if allowed.contains("creature") {
            targetAllowed = .creature
        } else if allowed.contains("hero") {
            targetAllowed = .hero
        } else {
            targetAllowed = .both
        }

        return TargetRules(
            requiresTarget: requiresTarget,
            allowed: targetAllowed,
            scope: scope,
            bypassTaunt: bypassTaunt
        )
    }

    private func appendUpdates(from payload: JSONValue, publishLiveBatch: Bool = false) {
        guard let rawUpdates = payload["updates"]?.arrayValue else {
            return
        }

        var nextUpdates = updates
        var newUpdates: [GameUpdateSnapshot] = []
        for update in rawUpdates {
            let snapshot = GameUpdateSnapshot(
                id: updateId(update),
                value: update
            )
            guard !nextUpdates.contains(where: { $0.id == snapshot.id }) else {
                continue
            }
            nextUpdates.append(snapshot)
            newUpdates.append(snapshot)
        }

        if nextUpdates.count > 160 {
            nextUpdates = Array(nextUpdates.suffix(160))
        }
        updates = nextUpdates

        guard publishLiveBatch, !newUpdates.isEmpty else {
            return
        }
        liveUpdateBatch = newUpdates
        liveUpdateBatchId += 1
    }

    private func payloadIncludesGameOverUpdate(_ payload: JSONValue) -> Bool {
        payload["updates"]?.arrayValue?.contains { update in
            update["type"]?.stringValue == "update_game_over"
        } ?? false
    }

    private func appendErrors(from payload: JSONValue) {
        guard let errors = payload["errors"]?.arrayValue, !errors.isEmpty else {
            return
        }

        errorMessage = errors
            .compactMap { $0["reason"]?.stringValue }
            .joined(separator: "\n")
    }

    private func updateId(_ update: JSONValue) -> String {
        let id = [
            update["timestamp"]?.stringValue,
            update["type"]?.stringValue,
            update["side"]?.stringValue,
            update["source_id"]?.stringValue,
            update["target_id"]?.stringValue,
            update["card_id"]?.stringValue,
        ]
            .compactMap { $0 }
            .joined(separator: "-")
        return id.isEmpty ? UUID().uuidString : id
    }

    private func entityName(type: String?, id: String?, side: String) -> String? {
        guard let id else {
            return nil
        }

        if type == "hero" {
            for heroSide in ["side_a", "side_b"] {
                let hero = gameJSON?["heroes"]?[heroSide]
                if hero?["hero_id"]?.stringValue == id || heroSide == id {
                    return hero?["player_name"]?.stringValue ?? hero?["name"]?.stringValue
                }
            }
            return gameJSON?["heroes"]?[side]?["name"]?.stringValue
        }

        if type == "creature" || type == "board" {
            return gameJSON?["creatures"]?[id]?["name"]?.stringValue
        }

        if type == "card" || type == nil {
            return gameJSON?["cards"]?[id]?["name"]?.stringValue
                ?? gameJSON?["creatures"]?[id]?["name"]?.stringValue
        }

        return nil
    }

    private func guestQueryItems(_ token: String) -> [URLQueryItem] {
        [URLQueryItem(name: "guest_token", value: token)]
    }
}

struct GameDetailView: View {
    @EnvironmentObject private var authStore: AuthStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var model = GameDetailViewModel()
    @StateObject private var socket = DrawTwoWebSocket()
    @State private var overlay: GameOverlay?
    @State private var selectedMulliganCardIds: Set<String> = []
    @State private var now = Date()
    @State private var showGameOverOverlay = true
    @State private var showConcedeConfirmation = false
    @State private var autoSwitchTarget: GameSummary?
    @State private var isAutoSwitchingGame = false
    @State private var isIntroRestartLoading = false
    @State private var autoSwitchTask: Task<Void, Never>?
    #if DEBUG
    @State private var didApplyInitialGameOverlay = false
    @State private var didApplyInitialGameCommand = false
    #endif

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
    private let autoSwitchNavigateDelayNs: UInt64 = 760_000_000

    let gameId: Int
    var guestAccessToken: String? = nil
    var onOpenGame: (Int) -> Void = { _ in }
    var onOpenIntroGame: (Int, String) -> Void = { _, _ in }
    var onIntroSignUp: () -> Void = {}

    var body: some View {
        ArchetypeScreen {
            ZStack {
                VStack(spacing: 0) {
                    NativeBoardSurface(
                        model: model,
                        socketStatus: socket.status,
                        gameId: gameId,
                        timeText: model.timeLeftString(now: now),
                        isMulliganPhase: model.isMulliganPhase,
                        onHandCardTap: handleHandCardTap,
                        onOwnCreatureTap: handleOwnCreatureTap,
                        onOpponentCreatureTap: handleOpponentCreatureTap,
                        onOwnHeroTap: handleOwnHeroTap,
                        onOpponentHeroTap: handleOpponentHeroTap,
                        onUpdatesTap: { overlay = .updates },
                        onMenuTap: openMenu,
                        isAutoSwitchingGame: isAutoSwitchingGame,
                        onEndTurn: sendEndTurn
                    )

                    if model.errorMessage != nil || model.statusMessage != nil {
                        boardMessages
                            .padding(.horizontal, 14)
                            .padding(.vertical, 10)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                if model.isMulliganPhase {
                    MulliganOverlay(
                        cards: model.mulliganCards(),
                        isDone: model.ownMulliganDone,
                        selectedIds: $selectedMulliganCardIds,
                        onSubmit: submitMulligan
                    )
                }

                if model.isMulliganPhase, overlay == nil, model.winner == "none" {
                    MulliganMenuButtonLayer(
                        socketStatus: socket.status,
                        onMenuTap: openMenu
                    )
                }

                if model.winner != "none", showGameOverOverlay {
                    GameOverOverlay(
                        title: gameOverTitle,
                        winnerText: winnerText,
                        isVictory: model.winner == model.viewerSide,
                        eloChange: model.eloChange,
                        isIntroGame: isIntroGuestGame,
                        canRematch: model.canRequestRematch,
                        isRematchLoading: model.isRematchLoading,
                        isIntroRetryLoading: isIntroRestartLoading,
                        noticeText: model.statusMessage ?? model.errorMessage,
                        noticeColor: model.statusMessage == nil ? ArchetypeTheme.red : ArchetypeTheme.green,
                        onExit: { dismiss() },
                        onRematch: requestRematch,
                        onIntroSignUp: openIntroSignUp,
                        onIntroRetry: restartIntroGame,
                        onReturn: { showGameOverOverlay = false }
                    )
                }

                if let overlay {
                    overlayContent(overlay)
                }

                if let autoSwitchTarget {
                    AutoSwitchGameOverlay(gameName: autoSwitchTarget.name)
                        .transition(.opacity.combined(with: .scale(scale: 0.985)))
                        .zIndex(80)
                }
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .confirmationDialog(
            "Concede this game?",
            isPresented: $showConcedeConfirmation,
            titleVisibility: .visible
        ) {
            Button("Concede", role: .destructive) {
                sendConcede()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will end the game as a loss.")
        }
        .task(id: gameLoadKey) {
            prepareForGameLoad()
            await refreshCurrentGame()
        }
        .onDisappear {
            autoSwitchTask?.cancel()
            socket.sendPresence(active: false)
            socket.disconnect()
            socket.onTextMessage = nil
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else {
                socket.sendPresence(active: false)
                socket.disconnect()
                model.prepareForSocketSnapshotSync()
                return
            }
            Task {
                await refreshCurrentGame()
            }
        }
        .onChange(of: model.phase) { _, phase in
            if phase != "mulligan" {
                selectedMulliganCardIds = []
            }
            recordCaptureState()
        }
        .onChange(of: model.winner) { _, winner in
            if winner != "none" {
                showGameOverOverlay = true
                fetchEloChangeIfNeeded()
            }
            recordCaptureState()
        }
        .onChange(of: model.liveGameOverVersion) { _, _ in
            acknowledgeActiveGameOverNotification()
        }
        .onChange(of: model.displayUpdates.count) { _, _ in
            recordCaptureState()
        }
        .onChange(of: overlay?.id) { _, _ in
            recordCaptureState()
        }
        .onChange(of: socket.messagesReceived) { _, _ in
            #if DEBUG
            applyInitialGameCommandIfNeeded()
            #endif
            recordCaptureState()
        }
        .onReceive(timer) { date in
            now = date
        }
    }

    private func recordCaptureState() {
        var detail = [
            "game_id": "\(gameId)",
            "phase": model.phase,
            "winner": model.winner,
            "update_count": "\(model.displayUpdates.count)",
            "socket_messages": "\(socket.messagesReceived)",
            "socket_status": socket.status.rawValue,
        ]

        if let overlay {
            detail["overlay"] = overlay.captureScreenName
        }

        if let latestUpdate = model.displayUpdates.last {
            detail["latest_update_type"] = latestUpdate.type
        }

        if model.displayUpdates.contains(where: { $0.type == "update_end_turn" }) {
            detail["has_end_turn_update"] = "1"
        }

        if let errorMessage = model.errorMessage, !errorMessage.isEmpty {
            detail["model_error"] = errorMessage
        }

        CaptureStateRecorder.record(currentCaptureScreenName, detail: detail)
    }

    private var currentCaptureScreenName: String {
        if let overlay {
            return overlay.captureScreenName
        }

        if model.winner != "none", showGameOverOverlay {
            return "game-over-ranked"
        }

        if model.isMulliganPhase {
            return "game-mulligan"
        }

        return "game-board"
    }

    private var winnerText: String {
        if model.winner == model.viewerSide {
            return "You won this match."
        }
        if model.winner == model.opponentSide {
            return "Your opponent won this match."
        }
        return "\(model.winner) wins."
    }

    private var isIntroGuestGame: Bool {
        guestAccessToken != nil || model.gameType == "intro"
    }

    private var gameLoadKey: String {
        "\(gameId):\(guestAccessToken ?? "")"
    }

    private var gameOverTitle: String {
        if isIntroGuestGame, model.winner == model.viewerSide {
            return "Intro Complete!"
        }
        return model.currentGameOverTitle
    }

    private var boardMessages: some View {
        VStack(spacing: 8) {
            if let error = model.errorMessage {
                Text(error)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.red)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(ArchetypeTheme.red.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            }

            if let status = model.statusMessage {
                Text(status)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.green)
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(ArchetypeTheme.green.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
            }
        }
    }

    private func prepareForGameLoad() {
        autoSwitchTask?.cancel()
        autoSwitchTask = nil
        autoSwitchTarget = nil
        isAutoSwitchingGame = false
        overlay = nil
        selectedMulliganCardIds = []
        showConcedeConfirmation = false
        showGameOverOverlay = true
        model.resetForGameLoad()
        socket.disconnect()
        socket.onTextMessage = { text in
            let wasActionRequired = model.isPlayerActionRequired
            model.applySocketText(text)
            let isActionRequired = model.isPlayerActionRequired
            guard guestAccessToken == nil, wasActionRequired != isActionRequired else {
                return
            }
            Task {
                await PushNotificationManager.shared.refreshBadgeCount(using: authStore)
            }
        }
        #if DEBUG
        didApplyInitialGameCommand = false
        didApplyInitialGameOverlay = false
        #endif
    }

    private func refreshCurrentGame() async {
        await model.load(gameId: gameId, using: authStore, guestAccessToken: guestAccessToken)
        await model.loadActiveGames(using: authStore, guestAccessToken: guestAccessToken)
        await model.fetchEloChangeIfNeeded(
            gameId: gameId,
            using: authStore,
            guestAccessToken: guestAccessToken
        )
        connectSocketIfPossible()
        #if DEBUG
        applyInitialGameCommandIfNeeded()
        applyInitialGameOverlayIfNeeded()
        #endif
        recordCaptureState()
    }

    private func connectSocketIfPossible() {
        if let guestAccessToken {
            model.prepareForSocketSnapshotSync()
            socket.connect(path: "/ws/game/\(gameId)/", guestToken: guestAccessToken)
            socket.sendPresence(active: scenePhase == .active)
            return
        }

        guard let accessToken = authStore.currentAccessToken else {
            return
        }
        model.prepareForSocketSnapshotSync()
        socket.connect(path: "/ws/game/\(gameId)/", accessToken: accessToken)
        socket.sendPresence(active: scenePhase == .active)
    }

    @ViewBuilder
    private func overlayContent(_ overlay: GameOverlay) -> some View {
        switch overlay {
        case .entity(let context):
            EntityDetailSheet(
                context: context,
                playUnavailableReason: context.card.flatMap { model.cardPlayUnavailableReason($0) },
                attackUnavailableReason: context.card.flatMap { model.attackUnavailableReason($0) },
                heroPowerUnavailableReason: context.hero.flatMap { model.heroPowerUnavailableReason(for: $0.side) },
                spellRequiresTarget: context.card.map {
                    $0.isSpell && model.targetRules(for: $0).requiresTarget
                } ?? false,
                onPlayCard: playCardFromDetail,
                onAttack: beginAttack,
                onUseHero: beginHeroPower,
                onDismiss: { self.overlay = nil }
            )
        case .placement(let context):
            PlacementSheet(
                context: context,
                onSelectPosition: { position in
                    playCreature(context.card, at: position)
                },
                onDismiss: { self.overlay = nil }
            )
        case .targeting(let context):
            TargetingSheet(
                context: context,
                options: model.targetOptions(for: context),
                onSelectTarget: { option in
                    selectTarget(option, for: context)
                },
                onDismiss: { self.overlay = nil }
            )
        case .updates:
            UpdatesSheet(
                updates: model.displayUpdates,
                viewerSide: model.viewerSide,
                heroName: { side in
                    model.snapshot(for: side, label: side).heroName
                },
                heroSnapshot: { side in
                    model.snapshot(for: side, label: side)
                },
                updateCard: { update in
                    model.updateCardSnapshot(update)
                },
                updateEntity: { type, id, side in
                    model.updateEntitySnapshot(type: type, id: id, side: side)
                },
                updateText: { update, hideSource in
                    model.updateText(update, hideSource: hideSource)
                },
                onDismiss: { self.overlay = nil }
            )
        case .howToPlay:
            GameHowToPlaySheet(
                onDismiss: { self.overlay = nil }
            )
        case .menu:
            GameMenuSheet(
                latestUpdateText: model.latestDisplayUpdateText,
                nextGame: model.nextGame(currentGameId: gameId),
                canExtendTime: model.canExtendTime,
                canConcede: model.winner == "none",
                onNextGame: openNextGame,
                onUpdates: { self.overlay = .updates },
                onHowToPlay: { self.overlay = .howToPlay },
                onExtendTime: sendExtendTime,
                onConcede: requestConcede,
                onExit: { dismiss() },
                onDismiss: { self.overlay = nil }
            )
        }
    }

    private func handleHandCardTap(_ card: BoardCardSnapshot) {
        let rules = model.targetRules(for: card)
        if card.isSpell, rules.requiresTarget, model.cardPlayUnavailableReason(card) == nil {
            beginTargeting(
                title: "Cast Spell",
                sourceName: card.shortName,
                sourceCard: card,
                rules: rules,
                unavailableReason: nil,
                command: .playCard(cardId: card.id, position: 0)
            )
            return
        }

        overlay = .entity(
            GameEntityDetailContext(
                kind: .handCard,
                card: card,
                hero: nil
            )
        )
    }

    private func handleOwnCreatureTap(_ card: BoardCardSnapshot) {
        if model.attackUnavailableReason(card) == nil {
            beginAttack(card)
            return
        }

        overlay = .entity(
            GameEntityDetailContext(
                kind: .ownCreature,
                card: card,
                hero: nil
            )
        )
    }

    private func handleOpponentCreatureTap(_ card: BoardCardSnapshot) {
        overlay = .entity(
            GameEntityDetailContext(
                kind: .opponentCreature,
                card: card,
                hero: nil
            )
        )
    }

    private func handleOwnHeroTap(_ hero: GameSideSnapshot) {
        overlay = .entity(
            GameEntityDetailContext(
                kind: .ownHero,
                card: nil,
                hero: hero
            )
        )
    }

    private func handleOpponentHeroTap(_ hero: GameSideSnapshot) {
        overlay = .entity(
            GameEntityDetailContext(
                kind: .opponentHero,
                card: nil,
                hero: hero
            )
        )
    }

    private func playCardFromDetail(_ card: BoardCardSnapshot) {
        guard model.cardPlayUnavailableReason(card) == nil else {
            return
        }

        if card.isSpell {
            let rules = model.targetRules(for: card)
            if rules.requiresTarget {
                beginTargeting(
                    title: "Cast Spell",
                    sourceName: card.shortName,
                    sourceCard: card,
                    rules: rules,
                    unavailableReason: nil,
                    command: .playCard(cardId: card.id, position: 0)
                )
            } else {
                sendPlayCard(card.id, position: 0)
                overlay = nil
            }
            return
        }

        let boardCards = model.boardCards(for: model.viewerSide)
        guard !boardCards.isEmpty else {
            playCreature(card, at: 0)
            return
        }

        overlay = .placement(
            GamePlacementContext(
                card: card,
                boardCards: boardCards
            )
        )
    }

    private func playCreature(_ card: BoardCardSnapshot, at position: Int) {
        let rules = model.targetRules(for: card, battlecryOnly: true)
        if rules.requiresTarget {
            beginTargeting(
                title: "Battlecry Target",
                sourceName: card.shortName,
                sourceCard: card,
                rules: rules,
                unavailableReason: nil,
                command: .playCard(cardId: card.id, position: position)
            )
        } else {
            sendPlayCard(card.id, position: position)
            overlay = nil
        }
    }

    private func beginAttack(_ card: BoardCardSnapshot) {
        beginTargeting(
            title: "Select Attack Target",
            sourceName: card.shortName,
            sourceCard: card,
            rules: TargetRules(
                requiresTarget: true,
                allowed: .both,
                scope: .enemy,
                bypassTaunt: false
            ),
            unavailableReason: model.attackUnavailableReason(card),
            command: .attack(cardId: card.id)
        )
    }

    private func beginHeroPower(_ hero: GameSideSnapshot) {
        guard let heroId = hero.heroId else {
            return
        }

        let unavailableReason = model.heroPowerUnavailableReason(for: hero.side)
        let rules = model.heroTargetRules(for: hero.side)

        if unavailableReason == nil, !rules.requiresTarget {
            socket.send(json: [
                "type": "cmd_use_hero",
                "hero_id": heroId,
                "target_id": heroId,
                "target_type": "hero",
            ])
            overlay = nil
            return
        }

        beginTargeting(
            title: "Use Hero Power",
            sourceName: hero.heroPowerName ?? "Hero Power",
            sourceCard: nil,
            rules: rules,
            unavailableReason: unavailableReason,
            command: .heroPower(heroId: heroId)
        )
    }

    private func beginTargeting(
        title: String,
        sourceName: String,
        sourceCard: BoardCardSnapshot?,
        rules: TargetRules,
        unavailableReason: String?,
        command: PendingGameCommand
    ) {
        overlay = .targeting(
            GameTargetingContext(
                title: title,
                sourceName: sourceName,
                sourceCard: sourceCard,
                allowed: rules.allowed,
                scope: rules.scope,
                bypassTaunt: rules.bypassTaunt,
                unavailableReason: unavailableReason,
                command: command
            )
        )
    }

    private func selectTarget(_ option: GameTargetOption, for context: GameTargetingContext) {
        guard option.enabled else {
            return
        }
        guard let target = model.commandTargetPayload(option: option, command: context.command) else {
            return
        }

        switch context.command {
        case .playCard(let cardId, let position):
            sendPlayCard(
                cardId,
                position: position,
                targetType: target.targetType,
                targetId: target.targetId
            )
        case .attack(let cardId):
            socket.send(json: [
                "type": "cmd_attack",
                "card_id": cardId,
                "target_type": target.targetType,
                "target_id": target.targetId,
            ])
        case .heroPower(let heroId):
            socket.send(json: [
                "type": "cmd_use_hero",
                "hero_id": heroId,
                "target_type": target.targetType,
                "target_id": target.targetId,
            ])
        }

        overlay = nil
    }

    private func sendPlayCard(
        _ cardId: String,
        position: Int,
        targetType: String? = nil,
        targetId: String? = nil
    ) {
        var command: [String: Any] = [
            "type": "cmd_play_card",
            "card_id": cardId,
            "position": position,
        ]
        if let targetType, let targetId {
            command["target_type"] = targetType
            command["target_id"] = targetId
        }
        socket.send(json: command)
    }

    private func sendEndTurn() {
        sendTurnPassingCommand(["type": "cmd_end_turn"])
    }

    private func sendTurnPassingCommand(_ command: [String: Any]) {
        guard !isAutoSwitchingGame else {
            return
        }

        socket.send(json: command)
        guard guestAccessToken == nil else {
            return
        }

        isAutoSwitchingGame = true
        autoSwitchTask?.cancel()
        autoSwitchTask = Task { @MainActor in
            await model.loadActiveGames(using: authStore)
            guard !Task.isCancelled else {
                isAutoSwitchingGame = false
                return
            }

            guard let nextGame = model.nextGame(currentGameId: gameId) else {
                isAutoSwitchingGame = false
                return
            }

            withAnimation(.easeOut(duration: 0.18)) {
                autoSwitchTarget = nextGame
            }

            do {
                try await Task.sleep(nanoseconds: autoSwitchNavigateDelayNs)
            } catch {
                isAutoSwitchingGame = false
                autoSwitchTarget = nil
                return
            }

            guard !Task.isCancelled else {
                isAutoSwitchingGame = false
                autoSwitchTarget = nil
                return
            }

            socket.disconnect()
            isAutoSwitchingGame = false
            autoSwitchTarget = nil
            onOpenGame(nextGame.id)
        }
    }

    private func requestConcede() {
        overlay = nil
        showConcedeConfirmation = true
    }

    private func sendConcede() {
        socket.send(json: ["type": "cmd_concede"])
        overlay = nil
    }

    private func sendExtendTime() {
        socket.send(json: ["type": "cmd_extend_time"])
        overlay = nil
    }

    private func openMenu() {
        overlay = .menu
        if guestAccessToken == nil {
            Task {
                await model.loadActiveGames(using: authStore)
            }
        }
    }

    private func openNextGame(_ game: GameSummary) {
        autoSwitchTask?.cancel()
        socket.disconnect()
        overlay = nil
        onOpenGame(game.id)
    }

    private func requestRematch() {
        Task {
            if await model.requestRematch(gameId: gameId, using: authStore) {
                dismiss()
            }
        }
    }

    private func fetchEloChangeIfNeeded() {
        Task {
            await model.fetchEloChangeIfNeeded(
                gameId: gameId,
                using: authStore,
                guestAccessToken: guestAccessToken
            )
        }
    }

    private func acknowledgeActiveGameOverNotification() {
        guard guestAccessToken == nil else {
            return
        }

        Task {
            do {
                let _: EmptyResponse = try await authStore.authenticatedPost(
                    "/gameplay/games/\(gameId)/notifications/read/",
                    body: EmptyBody()
                )
            } catch {
                // Best effort: leave the dashboard notification if this fails.
            }
        }
    }

    private func openIntroSignUp() {
        socket.disconnect()
        onIntroSignUp()
    }

    private func restartIntroGame() {
        guard !isIntroRestartLoading else {
            return
        }

        isIntroRestartLoading = true
        Task {
            do {
                let response: IntroScenarioStartResponse = try await APIClient.shared.post(
                    "/gameplay/scenarios/\(AppConfig.introScenarioSlug)/start/",
                    body: EmptyBody()
                )
                socket.disconnect()
                onOpenIntroGame(response.id, response.accessToken)
            } catch {
                model.errorMessage = error.localizedDescription
                showGameOverOverlay = false
            }

            isIntroRestartLoading = false
        }
    }

    private func submitMulligan() {
        guard !isAutoSwitchingGame else {
            return
        }

        let cardIds = Array(selectedMulliganCardIds).sorted()
        selectedMulliganCardIds = []
        sendTurnPassingCommand([
            "type": "cmd_mulligan",
            "card_ids": cardIds,
        ])
    }

    #if DEBUG
    private func applyInitialGameCommandIfNeeded() {
        guard !didApplyInitialGameCommand, let commandName = AppConfig.initialGameCommand else {
            return
        }
        guard socket.messagesReceived > 0 else {
            return
        }

        didApplyInitialGameCommand = true
        let shouldOpenUpdates = !commandName.hasSuffix("_board")
        let normalizedCommandName = commandName.replacingOccurrences(of: "_board", with: "")

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
            switch normalizedCommandName {
            case "zap_first_enemy", "spell_first_enemy", "cast_spell":
                sendFirstPlayableTargetedSpell(openUpdates: shouldOpenUpdates)
            case "attack_first_enemy", "attack":
                sendFirstAvailableAttack(openUpdates: shouldOpenUpdates)
            case "hero_power_self", "hero_power":
                sendHeroPowerAtFirstTarget(openUpdates: shouldOpenUpdates)
            case "play_first_creature", "play_creature":
                sendFirstPlayableCreature(openUpdates: shouldOpenUpdates)
            case "end_turn", "end-turn":
                sendEndTurn()
                showUpdatesAfterDebugCommand(openUpdates: shouldOpenUpdates)
            default:
                break
            }
        }
    }

    private func showUpdatesAfterDebugCommand(openUpdates: Bool) {
        guard openUpdates else {
            overlay = nil
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.15) {
            overlay = .updates
        }
    }

    private func sendFirstPlayableTargetedSpell(openUpdates: Bool) {
        guard let card = model.handCards(for: model.viewerSide).first(where: {
            $0.isSpell
                && model.cardPlayUnavailableReason($0) == nil
                && model.targetRules(for: $0).requiresTarget
        }) else {
            overlay = .updates
            return
        }

        let rules = model.targetRules(for: card)
        let context = GameTargetingContext(
            title: "Cast Spell",
            sourceName: card.shortName,
            sourceCard: card,
            allowed: rules.allowed,
            scope: rules.scope,
            bypassTaunt: rules.bypassTaunt,
            unavailableReason: nil,
            command: .playCard(cardId: card.id, position: 0)
        )
        guard let option = preferredTargetOption(for: context) else {
            overlay = .updates
            return
        }

        selectTarget(option, for: context)
        showUpdatesAfterDebugCommand(openUpdates: openUpdates)
    }

    private func sendFirstAvailableAttack(openUpdates: Bool) {
        guard let card = model.boardCards(for: model.viewerSide).first(where: {
            model.attackUnavailableReason($0) == nil
        }) else {
            overlay = .updates
            return
        }

        let context = GameTargetingContext(
            title: "Select Attack Target",
            sourceName: card.shortName,
            sourceCard: card,
            allowed: .both,
            scope: .enemy,
            bypassTaunt: false,
            unavailableReason: nil,
            command: .attack(cardId: card.id)
        )
        guard let option = preferredTargetOption(for: context) else {
            overlay = .updates
            return
        }

        selectTarget(option, for: context)
        showUpdatesAfterDebugCommand(openUpdates: openUpdates)
    }

    private func sendHeroPowerAtFirstTarget(openUpdates: Bool) {
        let hero = model.snapshot(for: model.viewerSide, label: "You")
        guard let heroId = hero.heroId, model.heroPowerUnavailableReason(for: hero.side) == nil else {
            overlay = .updates
            return
        }

        let rules = model.heroTargetRules(for: hero.side)
        let context = GameTargetingContext(
            title: "Use Hero Power",
            sourceName: hero.heroPowerName ?? "Hero Power",
            sourceCard: nil,
            allowed: rules.allowed,
            scope: rules.scope,
            bypassTaunt: rules.bypassTaunt,
            unavailableReason: nil,
            command: .heroPower(heroId: heroId)
        )
        guard let option = preferredTargetOption(for: context) else {
            overlay = .updates
            return
        }

        selectTarget(option, for: context)
        showUpdatesAfterDebugCommand(openUpdates: openUpdates)
    }

    private func sendFirstPlayableCreature(openUpdates: Bool) {
        guard let card = model.handCards(for: model.viewerSide).first(where: {
            !$0.isSpell && model.cardPlayUnavailableReason($0) == nil
        }) else {
            overlay = .updates
            return
        }

        sendPlayCard(
            card.id,
            position: model.boardCards(for: model.viewerSide).count
        )
        showUpdatesAfterDebugCommand(openUpdates: openUpdates)
    }

    private func preferredTargetOption(for context: GameTargetingContext) -> GameTargetOption? {
        let options = model.targetOptions(for: context).filter(\.enabled)
        return options.first { option in
            if case .creature = option.kind {
                return true
            }
            return false
        } ?? options.first
    }

    private func applyInitialGameOverlayIfNeeded() {
        guard !didApplyInitialGameOverlay, let overlayName = AppConfig.initialGameOverlay else {
            return
        }

        didApplyInitialGameOverlay = true

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            switch overlayName {
            case "menu":
                overlay = .menu
            case "updates":
                overlay = .updates
            case "hand", "card", "hand_card", "entity_card":
                if let card = model.handCards(for: model.viewerSide).first {
                    handleHandCardTap(card)
                }
            case "hand_spell", "spell_card", "entity_spell_card":
                if let card = model.handCards(for: model.viewerSide).first(where: {
                    $0.isSpell && !model.targetRules(for: $0).requiresTarget
                }) {
                    overlay = .entity(
                        GameEntityDetailContext(kind: .handCard, card: card, hero: nil)
                    )
                }
            case "hand_creature", "creature_card", "entity_creature_card":
                if let card = model.handCards(for: model.viewerSide).first(where: { !$0.isSpell }) {
                    overlay = .entity(
                        GameEntityDetailContext(kind: .handCard, card: card, hero: nil)
                    )
                }
            case "placement", "place_creature":
                if let card = model.handCards(for: model.viewerSide).first(where: { !$0.isSpell }) {
                    overlay = .placement(
                        GamePlacementContext(
                            card: card,
                            boardCards: model.boardCards(for: model.viewerSide)
                        )
                    )
                }
            case "spell_target", "target_spell", "targeting_spell":
                if let card = model.handCards(for: model.viewerSide).first(where: {
                    $0.isSpell && model.targetRules(for: $0).requiresTarget
                }) {
                    beginTargeting(
                        title: "Cast Spell",
                        sourceName: card.shortName,
                        sourceCard: card,
                        rules: model.targetRules(for: card),
                        unavailableReason: model.cardPlayUnavailableReason(card),
                        command: .playCard(cardId: card.id, position: 0)
                    )
                }
            case "own_hero", "hero_power":
                overlay = .entity(
                    GameEntityDetailContext(
                        kind: .ownHero,
                        card: nil,
                        hero: model.snapshot(for: model.viewerSide, label: "You")
                    )
                )
            case "opponent_hero":
                overlay = .entity(
                    GameEntityDetailContext(
                        kind: .opponentHero,
                        card: nil,
                        hero: model.snapshot(for: model.opponentSide, label: "Opponent")
                    )
                )
            case "own_creature", "own_creature_attack":
                if let card = model.boardCards(for: model.viewerSide).first {
                    beginAttack(card)
                }
            case "own_creature_detail":
                if let card = model.boardCards(for: model.viewerSide).first {
                    overlay = .entity(
                        GameEntityDetailContext(kind: .ownCreature, card: card, hero: nil)
                    )
                }
            case "opponent_creature":
                if let card = model.boardCards(for: model.opponentSide).first {
                    overlay = .entity(
                        GameEntityDetailContext(kind: .opponentCreature, card: card, hero: nil)
                    )
                }
            case "attack_target", "target_attack", "targeting_attack":
                if let card = model.boardCards(for: model.viewerSide).first {
                    beginAttack(card)
                }
            default:
                break
            }
        }
    }
    #endif
}

private struct NativeBoardSurface: View {
    @ObservedObject var model: GameDetailViewModel
    let socketStatus: SocketStatus
    let gameId: Int
    let timeText: String?
    let isMulliganPhase: Bool
    let onHandCardTap: (BoardCardSnapshot) -> Void
    let onOwnCreatureTap: (BoardCardSnapshot) -> Void
    let onOpponentCreatureTap: (BoardCardSnapshot) -> Void
    let onOwnHeroTap: (GameSideSnapshot) -> Void
    let onOpponentHeroTap: (GameSideSnapshot) -> Void
    let onUpdatesTap: () -> Void
    let onMenuTap: () -> Void
    let isAutoSwitchingGame: Bool
    let onEndTurn: () -> Void

    @State private var transientUpdate: GameUpdateSnapshot?
    @State private var transientUpdateId: String?
    @State private var transientAnimationId = UUID()
    @State private var combatAnimationQueue: [GameUpdateSnapshot] = []
    @State private var combatClearWorkItem: DispatchWorkItem?
    @State private var playedSpellCards: [BoardPlayedSpellCard] = []
    @State private var playedSpellHideWorkItems: [String: DispatchWorkItem] = [:]
    @State private var playedSpellRemoveWorkItems: [String: DispatchWorkItem] = [:]
    @State private var entityPointCache: [String: CGPoint] = [:]
    @State private var valueBursts: [BoardValueBurst] = []
    @State private var valueBurstRemoveWorkItems: [String: DispatchWorkItem] = [:]

    private static let combatAnimationDuration: TimeInterval = 0.62
    private static let valueBurstDuration: TimeInterval = 2.2
    private static let playedSpellCardDuration: TimeInterval = 1.7
    private static let playedSpellCardExitDuration: TimeInterval = 0.26
    private static let playedSpellCardAfterAnimationDuration: TimeInterval = 0.4

    private var opponent: GameSideSnapshot {
        model.snapshot(for: model.opponentSide, label: "Opponent")
    }

    private var player: GameSideSnapshot {
        model.snapshot(for: model.viewerSide, label: "You")
    }

    private var combatMarker: BoardCombatMarker? {
        guard let update = transientUpdate,
              var marker = BoardCombatMarker(update: update, viewerSide: model.viewerSide)
        else {
            return nil
        }

        marker.animationToken = transientAnimationId
        marker.sourcePoint = marker.sourceId.flatMap { entityPointCache[$0] }
        marker.targetPoint = marker.targetId.flatMap { entityPointCache[$0] }
        marker.isSpellSource = spellCard(
            sourceType: marker.sourceType,
            sourceId: marker.sourceId,
            side: update.side
        ) != nil
        marker.casterIsViewer = update.side == model.viewerSide
        return marker
    }

    var body: some View {
        VStack(spacing: 0) {
            BoardSideHeader(
                snapshot: opponent,
                isActive: model.activeSide == opponent.side,
                combatMarker: combatMarker,
                socketStatus: socketStatus,
                isTop: true,
                latestUpdate: model.displayUpdates.last,
                latestUpdateText: model.latestDisplayUpdateText,
                latestUpdateCompactText: model.latestDisplayUpdateCompactText,
                latestUpdateCard: model.displayUpdates.last.flatMap(model.updateCardSnapshot),
                latestUpdateActorHero: latestUpdateActorHero,
                latestSourceEntity: latestUpdateEntity(
                    typeKey: "source_type",
                    idKey: "source_id"
                ),
                latestTargetEntity: latestUpdateEntity(
                    typeKey: "target_type",
                    idKey: "target_id"
                ),
                isViewerUpdate: model.displayUpdates.last?.side == model.viewerSide,
                showsMenuButton: !isMulliganPhase,
                onHeroTap: { onOpponentHeroTap(opponent) },
                onCenterTap: onUpdatesTap,
                onMenuTap: onMenuTap
            )

            StatStrip(snapshot: opponent)

            BoardLane(
                cards: model.boardCards(for: opponent.side),
                combatMarker: combatMarker,
                isOpponent: true,
                onCardTap: onOpponentCreatureTap
            )
            .frame(maxHeight: .infinity)

            TurnDivider(
                turn: model.turn,
                timeText: timeText,
                isPlayerTurn: model.isPlayerTurn,
                highlightEndTurn: model.hasNoAvailableActions,
                isEndTurnDisabled: isAutoSwitchingGame,
                winnerText: winnerText,
                onEndTurn: onEndTurn
            )

            BoardLane(
                cards: model.boardCards(for: player.side),
                combatMarker: combatMarker,
                isOpponent: false,
                onCardTap: onOwnCreatureTap
            )
            .frame(maxHeight: .infinity)

            StatStrip(snapshot: player)

            PlayerFooter(
                snapshot: player,
                isActive: model.activeSide == player.side,
                isHeroDimmed: model.heroPowerUnavailableReason(for: player.side) != nil,
                combatMarker: combatMarker,
                handCards: model.handCards(for: player.side),
                isPlayable: model.isHandCardPlayable,
                onHeroTap: { onOwnHeroTap(player) },
                onCardTap: onHandCardTap
            )
        }
        .frame(maxWidth: 448)
        .frame(maxHeight: .infinity)
        .background(ArchetypeTheme.ink2, ignoresSafeAreaEdges: [])
        .overlayPreferenceValue(BoardEntityAnchorPreferenceKey.self) { anchors in
            GeometryReader { proxy in
                ZStack {
                    transientCombatOverlay(in: proxy.size, anchors: anchors, proxy: proxy)
                    playedSpellCardOverlay(in: proxy.size)
                    valueBurstOverlay
                }
                .onAppear {
                    cacheEntityPoints(anchors: anchors, proxy: proxy)
                }
                .onChange(of: entityAnchorCacheKey) { _, _ in
                    cacheEntityPoints(anchors: anchors, proxy: proxy)
                }
            }
            .allowsHitTesting(false)
        }
        .overlay(alignment: .leading) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(width: 1)
        }
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(width: 1)
        }
        .onChange(of: model.liveUpdateBatchId) { _, _ in
            triggerTransientCombatIfNeeded(from: model.liveUpdateBatch)
        }
        .onChange(of: gameId) { _, _ in
            resetTransientCombatState()
        }
        .onDisappear {
            resetTransientCombatState()
        }
    }

    private var entityAnchorCacheKey: String {
        (
            [
                opponent.side,
                opponent.heroId,
                player.side,
                player.heroId,
            ]
                .compactMap { $0 }
            + model.boardCards(for: opponent.side).map(\.id)
            + model.boardCards(for: player.side).map(\.id)
        )
        .joined(separator: "|")
    }

    private var winnerText: String? {
        guard model.winner != "none" else {
            return nil
        }

        if model.winner == model.viewerSide {
            return "You win!"
        }

        if model.winner == model.opponentSide {
            return "You lose!"
        }

        return "Game Over"
    }

    private var latestUpdateActorHero: GameSideSnapshot? {
        guard let updateSide = model.displayUpdates.last?.side else {
            return nil
        }

        return model.snapshot(
            for: updateSide,
            label: updateSide == model.viewerSide ? "You" : "Opponent"
        )
    }

    private func latestUpdateEntity(
        typeKey: String,
        idKey: String
    ) -> GameUpdateEntitySnapshot? {
        guard let update = model.displayUpdates.last else {
            return nil
        }
        return model.updateEntitySnapshot(
            type: update.value[typeKey]?.stringValue,
            id: update.value[idKey]?.stringValue,
            side: update.side
        )
    }

    @ViewBuilder
    private func transientCombatOverlay(
        in size: CGSize,
        anchors: [String: Anchor<CGRect>],
        proxy: GeometryProxy
    ) -> some View {
        if let update = transientUpdate,
           let combat = transientCombat(for: update, in: size, anchors: anchors, proxy: proxy) {
            BoardCombatAnimationLayer(combat: combat, onBegin: handleCombatBegan)
                .id(transientAnimationId)
        }
    }

    @ViewBuilder
    private var valueBurstOverlay: some View {
        ForEach(valueBursts) { burst in
            BoardValueBurstView(burst: burst)
        }
    }

    private func handleCombatBegan(_ combat: BoardTransientCombat) {
        spawnValueBurst(for: combat)

        let haptic = UIImpactFeedbackGenerator(style: combat.kind == .heal ? .soft : .medium)
        haptic.prepare()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            haptic.impactOccurred()
        }
    }

    private func spawnValueBurst(for combat: BoardTransientCombat) {
        guard combat.value > 0, !valueBursts.contains(where: { $0.id == combat.id }) else {
            return
        }

        valueBursts.append(
            BoardValueBurst(
                id: combat.id,
                kind: combat.kind,
                value: combat.value,
                point: combat.target
            )
        )

        let burstId = combat.id
        valueBurstRemoveWorkItems[burstId]?.cancel()
        let workItem = DispatchWorkItem {
            valueBursts.removeAll { $0.id == burstId }
            valueBurstRemoveWorkItems[burstId] = nil
        }
        valueBurstRemoveWorkItems[burstId] = workItem
        DispatchQueue.main.asyncAfter(
            deadline: .now() + Self.valueBurstDuration,
            execute: workItem
        )
    }

    @ViewBuilder
    private func playedSpellCardOverlay(in size: CGSize) -> some View {
        ForEach(playedSpellCards) { playedSpell in
            BoardPlayedSpellCardView(
                playedSpell: playedSpell,
                isBottomSide: playedSpell.side == player.side,
                point: spellSourcePoint(for: playedSpell.side, in: size)
            )
        }
    }

    private func triggerTransientCombatIfNeeded(from updates: [GameUpdateSnapshot]) {
        queuePlayedSpellCards(from: updates)

        for update in updates where canAnimate(update) {
            guard transientUpdateId != update.id,
                  !combatAnimationQueue.contains(where: { $0.id == update.id })
            else {
                continue
            }

            if let card = spellCard(
                sourceType: update.value["source_type"]?.stringValue,
                sourceId: update.value["source_id"]?.stringValue,
                side: update.side
            ) {
                showPlayedSpellCard(
                    card,
                    side: update.side,
                    duration: spellCardAnimationLingerDuration()
                )
            }

            combatAnimationQueue.append(update)
        }

        playNextTransientCombatIfNeeded()
    }

    private func playNextTransientCombatIfNeeded() {
        guard transientUpdate == nil, !combatAnimationQueue.isEmpty else {
            return
        }

        let update = combatAnimationQueue.removeFirst()
        transientUpdate = update
        transientUpdateId = update.id
        transientAnimationId = UUID()

        let updateId = update.id
        combatClearWorkItem?.cancel()

        let workItem = DispatchWorkItem {
            guard transientUpdateId == updateId else {
                return
            }
            transientUpdate = nil
            transientUpdateId = nil
            combatClearWorkItem = nil
            playNextTransientCombatIfNeeded()
        }
        combatClearWorkItem = workItem
        DispatchQueue.main.asyncAfter(
            deadline: .now() + Self.combatAnimationDuration,
            execute: workItem
        )
    }

    private func canAnimate(_ update: GameUpdateSnapshot) -> Bool {
        guard update.type == "update_damage" || update.type == "update_heal" else {
            return false
        }

        return update.value["target_id"]?.stringValue != nil
    }

    private func queuePlayedSpellCards(from updates: [GameUpdateSnapshot]) {
        for update in updates {
            if let card = playedSpellCard(from: update) {
                showPlayedSpellCard(card, side: update.side)
            }
        }
    }

    private func playedSpellCard(from update: GameUpdateSnapshot) -> BoardCardSnapshot? {
        guard update.type == "update_play_card" else {
            return nil
        }

        if let card = model.updateCardSnapshot(update), card.isSpell {
            return card
        }

        let cardId = update.value["card_id"]?.stringValue
            ?? update.value["source_id"]?.stringValue
        guard let cardId,
              case .card(let card) = model.updateEntitySnapshot(
                type: "card",
                id: cardId,
                side: update.side
              ),
              card.isSpell
        else {
            return nil
        }

        return card
    }

    private func spellCardAnimationLingerDuration() -> TimeInterval {
        let queuedAnimationCount = combatAnimationQueue.count + (transientUpdate == nil ? 0 : 1)
        return (Double(queuedAnimationCount) * Self.combatAnimationDuration)
            + Self.combatAnimationDuration
            + Self.playedSpellCardAfterAnimationDuration
    }

    private func showPlayedSpellCard(
        _ card: BoardCardSnapshot,
        side: String,
        duration: TimeInterval = Self.playedSpellCardDuration
    ) {
        let cardId = card.id

        playedSpellRemoveWorkItems[cardId]?.cancel()
        playedSpellRemoveWorkItems[cardId] = nil

        if playedSpellCards.contains(where: { $0.id == cardId }) {
            playedSpellCards = playedSpellCards.map { playedSpell in
                playedSpell.id == cardId
                    ? BoardPlayedSpellCard(
                        id: cardId,
                        side: side,
                        card: card,
                        isLeaving: false
                    )
                    : playedSpell
            }
        } else {
            playedSpellCards.append(
                BoardPlayedSpellCard(
                    id: cardId,
                    side: side,
                    card: card,
                    isLeaving: false
                )
            )
        }

        playedSpellHideWorkItems[cardId]?.cancel()

        let workItem = DispatchWorkItem {
            hidePlayedSpellCard(cardId)
        }
        playedSpellHideWorkItems[cardId] = workItem

        DispatchQueue.main.asyncAfter(
            deadline: .now() + max(duration, Self.playedSpellCardDuration),
            execute: workItem
        )
    }

    private func hidePlayedSpellCard(_ cardId: String) {
        playedSpellHideWorkItems[cardId] = nil

        guard playedSpellCards.contains(where: { $0.id == cardId && !$0.isLeaving }) else {
            return
        }

        playedSpellCards = playedSpellCards.map { playedSpell in
            playedSpell.id == cardId
                ? BoardPlayedSpellCard(
                    id: playedSpell.id,
                    side: playedSpell.side,
                    card: playedSpell.card,
                    isLeaving: true
                )
                : playedSpell
        }

        playedSpellRemoveWorkItems[cardId]?.cancel()
        let workItem = DispatchWorkItem {
            removePlayedSpellCard(cardId)
        }
        playedSpellRemoveWorkItems[cardId] = workItem

        DispatchQueue.main.asyncAfter(
            deadline: .now() + Self.playedSpellCardExitDuration,
            execute: workItem
        )
    }

    private func removePlayedSpellCard(_ cardId: String) {
        playedSpellHideWorkItems[cardId]?.cancel()
        playedSpellRemoveWorkItems[cardId]?.cancel()
        playedSpellHideWorkItems[cardId] = nil
        playedSpellRemoveWorkItems[cardId] = nil
        playedSpellCards.removeAll { $0.id == cardId }
    }

    private func resetTransientCombatState() {
        combatClearWorkItem?.cancel()
        combatClearWorkItem = nil
        transientUpdate = nil
        transientUpdateId = nil
        combatAnimationQueue = []

        for workItem in playedSpellHideWorkItems.values {
            workItem.cancel()
        }
        for workItem in playedSpellRemoveWorkItems.values {
            workItem.cancel()
        }
        playedSpellHideWorkItems = [:]
        playedSpellRemoveWorkItems = [:]
        playedSpellCards = []

        for workItem in valueBurstRemoveWorkItems.values {
            workItem.cancel()
        }
        valueBurstRemoveWorkItems = [:]
        valueBursts = []
        entityPointCache = [:]
    }

    private func cacheEntityPoints(
        anchors: [String: Anchor<CGRect>],
        proxy: GeometryProxy
    ) {
        guard !anchors.isEmpty else {
            return
        }

        var nextCache = entityPointCache
        for (id, anchor) in anchors {
            let rect = proxy[anchor]
            nextCache[id] = CGPoint(x: rect.midX, y: rect.midY)
        }
        entityPointCache = nextCache
    }

    private func transientCombat(
        for update: GameUpdateSnapshot,
        in size: CGSize,
        anchors: [String: Anchor<CGRect>],
        proxy: GeometryProxy
    ) -> BoardTransientCombat? {
        let sourceType = update.value["source_type"]?.stringValue
        let sourceId = update.value["source_id"]?.stringValue
        let targetType = update.value["target_type"]?.stringValue
        let targetId = update.value["target_id"]?.stringValue

        guard let targetId,
              let target = point(
                for: targetType,
                id: targetId,
                updateSide: update.side,
                in: size,
                anchors: anchors,
                proxy: proxy
              )
        else {
            return nil
        }

        let playedSpellCard = spellCard(sourceType: sourceType, sourceId: sourceId, side: update.side)
        let value: Int
        let kind: BoardCombatAnimationKind
        if update.type == "update_heal" {
            value = update.value["amount"]?.intValue ?? 0
            kind = .heal
        } else {
            value = update.value["damage"]?.intValue ?? 0
            kind = playedSpellCard == nil ? .damage : .spellDamage
        }

        let source = playedSpellCard == nil
            ? point(
                for: sourceType,
                id: sourceId,
                updateSide: update.side,
                in: size,
                anchors: anchors,
                proxy: proxy
              )
            : spellSourcePoint(for: update.side, in: size)

        return BoardTransientCombat(
            id: update.id,
            kind: kind,
            source: source ?? target,
            target: target,
            value: value,
            isRetaliation: update.value["is_retaliation"]?.boolValue ?? false
        )
    }

    private func spellCard(
        sourceType: String?,
        sourceId: String?,
        side: String
    ) -> BoardCardSnapshot? {
        guard sourceType == "card",
              let sourceId,
              case .card(let card) = model.updateEntitySnapshot(type: "card", id: sourceId, side: side),
              card.isSpell
        else {
            return nil
        }
        return card
    }

    private func point(
        for type: String?,
        id: String?,
        updateSide: String,
        in size: CGSize,
        anchors: [String: Anchor<CGRect>],
        proxy: GeometryProxy
    ) -> CGPoint? {
        guard let id else {
            return nil
        }

        if let anchor = anchors[id] {
            let rect = proxy[anchor]
            return CGPoint(x: rect.midX, y: rect.midY)
        }

        if let cachedPoint = entityPointCache[id] {
            return cachedPoint
        }

        if type == "hero" {
            if id == opponent.heroId || id == opponent.side {
                if let anchor = anchors[opponent.side] {
                    let rect = proxy[anchor]
                    return CGPoint(x: rect.midX, y: rect.midY)
                }
                return CGPoint(x: 48, y: 48)
            }
            if id == player.heroId || id == player.side {
                if let anchor = anchors[player.side] {
                    let rect = proxy[anchor]
                    return CGPoint(x: rect.midX, y: rect.midY)
                }
                return CGPoint(x: 48, y: max(size.height - 48, 48))
            }
        }

        if type == "creature" || type == "card" || type == "board" || type == nil {
            let opponentCards = model.boardCards(for: opponent.side)
            if let index = opponentCards.firstIndex(where: { $0.id == id }) {
                return cardPoint(index: index, count: opponentCards.count, isOpponent: true, in: size)
            }

            let playerCards = model.boardCards(for: player.side)
            if let index = playerCards.firstIndex(where: { $0.id == id }) {
                return cardPoint(index: index, count: playerCards.count, isOpponent: false, in: size)
            }
        }

        if updateSide == opponent.side {
            return CGPoint(x: size.width / 2, y: 76)
        }
        if updateSide == player.side {
            return CGPoint(x: size.width / 2, y: max(size.height - 76, 76))
        }
        return nil
    }

    private func spellSourcePoint(for side: String, in size: CGSize) -> CGPoint {
        if side == opponent.side {
            return CGPoint(x: size.width / 2, y: 76)
        }
        return CGPoint(x: size.width / 2, y: max(size.height - 76, 76))
    }

    private func cardPoint(index: Int, count: Int, isOpponent: Bool, in size: CGSize) -> CGPoint {
        let cardWidth: CGFloat = 56
        let spacing: CGFloat = 8
        let horizontalPadding: CGFloat = 16
        let groupWidth = CGFloat(count) * cardWidth + CGFloat(max(count - 1, 0)) * spacing
        let availableWidth = max(size.width - (horizontalPadding * 2), 0)
        let startX = groupWidth <= availableWidth
            ? (size.width - groupWidth) / 2
            : horizontalPadding
        let x = startX + CGFloat(index) * (cardWidth + spacing) + (cardWidth / 2)
        let fixedHeight: CGFloat = 96 + 56 + 58 + 56 + 96
        let laneHeight = max((size.height - fixedHeight) / 2, 96)
        let topLaneY = 96 + 56 + (laneHeight / 2)
        let bottomLaneY = 96 + 56 + laneHeight + 58 + (laneHeight / 2)
        return CGPoint(x: x, y: isOpponent ? topLaneY : bottomLaneY)
    }
}

private struct BoardSideHeader: View {
    let snapshot: GameSideSnapshot
    let isActive: Bool
    let combatMarker: BoardCombatMarker?
    let socketStatus: SocketStatus
    let isTop: Bool
    let latestUpdate: GameUpdateSnapshot?
    let latestUpdateText: String
    let latestUpdateCompactText: String
    let latestUpdateCard: BoardCardSnapshot?
    let latestUpdateActorHero: GameSideSnapshot?
    let latestSourceEntity: GameUpdateEntitySnapshot?
    let latestTargetEntity: GameUpdateEntitySnapshot?
    let isViewerUpdate: Bool
    var showsMenuButton = true
    let onHeroTap: () -> Void
    let onCenterTap: () -> Void
    let onMenuTap: () -> Void

    var body: some View {
        HStack(spacing: 0) {
            Button(action: onHeroTap) {
                HeroTile(
                    snapshot: snapshot,
                    isActive: isActive,
                    combatRole: combatMarker?.role(forHeroId: snapshot.heroId),
                    combatMotion: combatMarker?.motion(forHeroId: snapshot.heroId),
                    animationToken: combatMarker?.animationToken
                )
            }
            .buttonStyle(.plain)
            .frame(width: 96, height: 96)
            .anchorPreference(key: BoardEntityAnchorPreferenceKey.self, value: .bounds) { anchor in
                var anchors = [snapshot.side: anchor]
                if let heroId = snapshot.heroId {
                    anchors[heroId] = anchor
                }
                return anchors
            }

            Button(action: onCenterTap) {
                VStack {
                    if let latestUpdate {
                        LatestUpdateChip(
                            update: latestUpdate,
                            text: latestUpdateText,
                            compactText: latestUpdateCompactText,
                            card: latestUpdateCard,
                            actorHero: latestUpdateActorHero,
                            sourceEntity: latestSourceEntity,
                            targetEntity: latestTargetEntity,
                            isViewerUpdate: isViewerUpdate
                        )
                        .padding(.horizontal, 8)
                    } else {
                        Spacer(minLength: 0)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .buttonStyle(.plain)
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            Group {
                if showsMenuButton {
                    BoardMenuButton(socketStatus: socketStatus, onMenuTap: onMenuTap)
                } else {
                    Color.clear
                        .accessibilityHidden(true)
                }
            }
            .frame(width: 96)
            .frame(maxHeight: .infinity)
            .overlay(alignment: .leading) {
                Rectangle()
                    .fill(ArchetypeTheme.border)
                    .frame(width: 1)
            }
        }
        .frame(height: 96)
        .background(ArchetypeTheme.ink, ignoresSafeAreaEdges: [])
        .overlay(alignment: isTop ? .bottom : .top) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }

}

private struct PlayerFooter: View {
    let snapshot: GameSideSnapshot
    let isActive: Bool
    let isHeroDimmed: Bool
    let combatMarker: BoardCombatMarker?
    let handCards: [BoardCardSnapshot]
    let isPlayable: (BoardCardSnapshot) -> Bool
    let onHeroTap: () -> Void
    let onCardTap: (BoardCardSnapshot) -> Void

    var body: some View {
        HStack(spacing: 0) {
            Button(action: onHeroTap) {
                HeroTile(
                    snapshot: snapshot,
                    isActive: isActive,
                    isDimmed: isHeroDimmed,
                    combatRole: combatMarker?.role(forHeroId: snapshot.heroId),
                    combatMotion: combatMarker?.motion(forHeroId: snapshot.heroId),
                    animationToken: combatMarker?.animationToken
                )
            }
            .buttonStyle(.plain)
            .frame(width: 96, height: 96)
            .anchorPreference(key: BoardEntityAnchorPreferenceKey.self, value: .bounds) { anchor in
                var anchors = [snapshot.side: anchor]
                if let heroId = snapshot.heroId {
                    anchors[heroId] = anchor
                }
                return anchors
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(handCards) { card in
                        Button {
                            onCardTap(card)
                        } label: {
                            MiniGameCard(
                                card: card,
                                active: isPlayable(card),
                                inLane: false
                            )
                        }
                        .buttonStyle(.plain)
                        .frame(width: 56, height: 78)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 9)
            }
            .frame(maxHeight: .infinity)
        }
        .frame(height: 96)
        .background(ArchetypeTheme.ink)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct LatestUpdateChip: View {
    let update: GameUpdateSnapshot
    let text: String
    let compactText: String
    let card: BoardCardSnapshot?
    let actorHero: GameSideSnapshot?
    let sourceEntity: GameUpdateEntitySnapshot?
    let targetEntity: GameUpdateEntitySnapshot?
    let isViewerUpdate: Bool

    var body: some View {
        Group {
            switch update.type {
            case "update_draw_card":
                drawChip
            case "update_damage":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "\(update.value["damage"]?.intValue ?? 0)",
                        glyph: "⚔️",
                        color: ArchetypeTheme.red
                    ),
                    targetBorderColor: targetBorderColor
                )
            case "update_heal":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "\(update.value["amount"]?.intValue ?? 0)",
                        glyph: "💚",
                        color: ArchetypeTheme.green
                    ),
                    targetBorderColor: ArchetypeTheme.green
                )
            case "update_buff":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "+\(update.value["amount"]?.intValue ?? 0)",
                        glyph: "↑",
                        color: ArchetypeTheme.violet
                    ),
                    targetBorderColor: borderColor
                )
            case "update_remove":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "Remove",
                        glyph: "💀",
                        color: Color(hex: 0x4B5563)
                    ),
                    targetBorderColor: targetBorderColor
                )
            case "update_silence":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "Silence",
                        glyph: "🤫",
                        color: ArchetypeTheme.sky
                    ),
                    targetBorderColor: ArchetypeTheme.sky
                )
            case "update_summon":
                compactEntityAction(
                    badge: UpdateActionBadge(
                        text: "Summon",
                        glyph: "✨",
                        color: ArchetypeTheme.violet
                    ),
                    targetBorderColor: borderColor
                )
            default:
                playOrFallbackChip
            }
        }
        .accessibilityLabel(text)
    }

    @ViewBuilder
    private var drawChip: some View {
        if isViewerUpdate, let card {
            HStack(spacing: 12) {
                Text("Draw")
                    .font(.archetypeBody(16, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)

                UpdateCardThumb(card: card, borderColor: borderColor)
            }
            .frame(maxWidth: .infinity)
        } else if let actorHero {
            HStack(spacing: 12) {
                UpdateHeroThumb(hero: actorHero, borderColor: borderColor)

                Text("Draws a card")
                    .font(.archetypeBody(16, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .frame(maxWidth: .infinity)
        } else {
            fallbackChip
        }
    }

    @ViewBuilder
    private var playOrFallbackChip: some View {
        if let card {
            HStack(spacing: 12) {
                Text(compactText)
                    .font(.archetypeBody(16, weight: .medium))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)

                UpdateCardThumb(card: card, borderColor: borderColor)
            }
            .frame(maxWidth: .infinity)
        } else {
            fallbackChip
        }
    }

    @ViewBuilder
    private func compactEntityAction(
        badge: UpdateActionBadge,
        targetBorderColor: Color
    ) -> some View {
        if sourceEntity == nil && targetEntity == nil {
            fallbackChip
        } else {
            HStack(spacing: 9) {
                if let sourceEntity {
                    UpdateEntityThumb(entity: sourceEntity, borderColor: borderColor)
                }

                badge
                    .scaleEffect(0.9)

                if let targetEntity {
                    UpdateEntityThumb(entity: targetEntity, borderColor: targetBorderColor)
                }
            }
            .frame(maxWidth: .infinity)
            .scaleEffect(0.88)
        }
    }

    private var fallbackChip: some View {
        HStack(spacing: 8) {
            UpdateGlyph(type: update.type)
                .frame(width: 28, height: 28)

            Text(text)
                .font(.archetypeBody(12, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .minimumScaleFactor(0.78)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 9)
        .padding(.vertical, 7)
        .background(Color.black.opacity(0.22))
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(borderColor.opacity(0.74), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }

    private var borderColor: Color {
        isViewerUpdate ? ArchetypeTheme.green : ArchetypeTheme.red
    }

    private var targetBorderColor: Color {
        isViewerUpdate ? ArchetypeTheme.red : ArchetypeTheme.green
    }
}

private struct UpdateCardThumb: View {
    let card: BoardCardSnapshot
    let borderColor: Color

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(hex: 0xD1D5DB))

            if let artURL = card.artURL {
                CachedRemoteImage(url: artURL) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    cardFallback
                }
            } else {
                cardFallback
            }
        }
        .frame(width: 40, height: 56)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(borderColor, lineWidth: 2)
        )
        .accessibilityLabel(card.shortName)
    }

    private var cardFallback: some View {
        Color(hex: 0xD1D5DB)
    }
}

private struct HeroTile: View {
    let snapshot: GameSideSnapshot
    let isActive: Bool
    var isDimmed = false
    var combatRole: BoardCombatRole? = nil
    var combatMotion: BoardCombatMotion? = nil
    var animationToken: UUID? = nil

    private var outlineColor: Color? {
        if let combatRole {
            return combatRole.borderColor
        }
        if isActive {
            return ArchetypeTheme.gold2
        }
        return nil
    }

    var body: some View {
        ZStack {
            if let heroArtURL = snapshot.heroArtURL {
                CachedRemoteImage(url: heroArtURL) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    heroFallback
                }
            } else {
                heroFallback
            }

            Color.black.opacity(0.5)

            Text(healthText)
                .font(.archetypeBody(17, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)

        }
        .frame(width: 96, height: 96)
        .clipped()
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(width: 1)
        }
        .overlay {
            if let outlineColor {
                Rectangle()
                    .strokeBorder(outlineColor, lineWidth: 4)
            }
        }
        .opacity(isDimmed ? 0.35 : 1)
        .animation(.spring(response: 0.28, dampingFraction: 0.72), value: combatRole != nil)
        .modifier(BoardCombatMotionModifier(motion: combatMotion, token: animationToken))
    }

    private var heroFallback: some View {
        Color.clear
    }

    private var healthText: String {
        if let health = snapshot.health {
            return "\(health)"
        }
        return "-"
    }
}

private struct BoardMenuButton: View {
    let socketStatus: SocketStatus
    let onMenuTap: () -> Void

    var body: some View {
        Button(action: onMenuTap) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)

                Circle()
                    .fill(socketColor)
                    .frame(width: 8, height: 8)
                    .padding(.top, 8)
                    .padding(.trailing, 8)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Open game menu")
    }

    private var socketColor: Color {
        switch socketStatus {
        case .connected:
            return ArchetypeTheme.green
        case .connecting, .reconnecting:
            return ArchetypeTheme.gold2
        case .failed, .disconnected:
            return ArchetypeTheme.red
        }
    }
}

private struct MulliganMenuButtonLayer: View {
    let socketStatus: SocketStatus
    let onMenuTap: () -> Void

    var body: some View {
        GeometryReader { proxy in
            let boardWidth = min(proxy.size.width, 448)
            let tileLeft = max((proxy.size.width + boardWidth) / 2 - 96, 0)

            ZStack(alignment: .topLeading) {
                Canvas { context, _ in
                    context.fill(
                        Path(CGRect(x: tileLeft, y: 0, width: 96, height: 96)),
                        with: .color(ArchetypeTheme.ink2)
                    )
                    context.fill(
                        Path(CGRect(x: tileLeft, y: 0, width: 1, height: 96)),
                        with: .color(ArchetypeTheme.border)
                    )
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .allowsHitTesting(false)

                BoardMenuButton(socketStatus: socketStatus, onMenuTap: onMenuTap)
                    .frame(width: 96, height: 96)
                    .offset(x: tileLeft, y: 0)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .zIndex(90)
    }
}

private struct StatStrip: View {
    let snapshot: GameSideSnapshot

    var body: some View {
        HStack(spacing: 0) {
            CompactStat(label: "Deck", value: "\(snapshot.deckCount)")
            CompactStat(label: "Hand", value: "\(snapshot.handCount)")
            CompactStat(label: "Energy", value: "\(snapshot.energy)/\(snapshot.energyPool)")
        }
        .frame(height: 68)
        .background(ArchetypeTheme.ink)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct CompactStat: View {
    let label: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.archetypeBody(16))
                .foregroundStyle(Color(hex: 0x6B7280))
            Text(value)
                .font(.archetypeBody(16))
                .foregroundStyle(ArchetypeTheme.text)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct BoardLane: View {
    let cards: [BoardCardSnapshot]
    let combatMarker: BoardCombatMarker?
    let isOpponent: Bool
    let onCardTap: (BoardCardSnapshot) -> Void

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(hex: 0x1F2937),
                    Color(hex: 0x1F2937),
                ],
                startPoint: .top,
                endPoint: .bottom
            )

            GeometryReader { proxy in
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        Spacer(minLength: 0)

                        ForEach(cards) { card in
                            Button {
                                onCardTap(card)
                            } label: {
                                MiniGameCard(
                                    card: card,
                                    active: false,
                                    inLane: true,
                                    combatRole: combatMarker?.role(forCardId: card.id),
                                    combatMotion: combatMarker?.motion(forCardId: card.id),
                                    animationToken: combatMarker?.animationToken
                                )
                            }
                            .buttonStyle(.plain)
                            .frame(width: 56, height: 78)
                            .anchorPreference(key: BoardEntityAnchorPreferenceKey.self, value: .bounds) { anchor in
                                [card.id: anchor]
                            }
                        }

                        Spacer(minLength: 0)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 9)
                    .frame(minWidth: proxy.size.width, minHeight: proxy.size.height)
                }
            }
        }
        .overlay(alignment: isOpponent ? .bottom : .top) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct TurnDivider: View {
    let turn: String
    let timeText: String?
    let isPlayerTurn: Bool
    let highlightEndTurn: Bool
    let isEndTurnDisabled: Bool
    let winnerText: String?
    let onEndTurn: () -> Void

    var body: some View {
        HStack {
            Text("Turn \(turn)")
                .font(.archetypeBody(14, weight: .bold))
                .foregroundStyle(ArchetypeTheme.text)

            if let timeText {
                Text("[ \(timeText) ]")
                    .font(.archetypeBody(12, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.gold2)
            }

            Spacer()

            if let winnerText {
                StatusPill(text: winnerText, color: ArchetypeTheme.gold2)
            } else if isPlayerTurn {
                Button {
                    onEndTurn()
                } label: {
                    Text("End Turn")
                }
                .buttonStyle(SecondaryGameButtonStyle())
                .overlay(
                    RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                        .stroke(
                            ArchetypeTheme.gold2.opacity(highlightEndTurn ? 0.95 : 0),
                            lineWidth: 2
                        )
                )
                .shadow(
                    color: highlightEndTurn ? ArchetypeTheme.gold2.opacity(0.35) : Color.clear,
                    radius: highlightEndTurn ? 8 : 0
                )
                .disabled(isEndTurnDisabled)
                .opacity(isEndTurnDisabled ? 0.56 : 1)
            } else {
                StatusPill(text: "Waiting", color: ArchetypeTheme.muted)
            }
        }
        .frame(height: 56)
        .padding(.horizontal, 8)
        .background(ArchetypeTheme.ink)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct MiniGameCard: View {
    let card: BoardCardSnapshot
    let active: Bool
    let inLane: Bool
    var isLarge = false
    var combatRole: BoardCombatRole? = nil
    var combatMotion: BoardCombatMotion? = nil
    var animationToken: UUID? = nil

    private var badgeOffset: CGFloat {
        isLarge ? 12 : 4
    }

    private var displayedTraitIcon: String? {
        guard inLane else {
            return card.traitIcon
        }

        let priority: [(String, String)] = [
            ("taunt", "🛡️"),
            ("deathrattle", "💀"),
            ("triggered", "⚡️"),
            ("stealth", "👁️"),
            ("unique", "⭐"),
        ]

        return priority.first { card.traitTypes.contains($0.0) }?.1
    }

    private var borderColor: Color {
        if active {
            return ArchetypeTheme.gold2
        }
        if inLane && card.hasStealth {
            return ArchetypeTheme.violet
        }
        return Color(hex: 0x111827)
    }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: 0xD1D5DB))

            GeometryReader { proxy in
                Group {
                    if let artURL = card.artURL {
                        CachedRemoteImage(url: artURL) { image in
                            image
                                .resizable()
                                .scaledToFill()
                        } placeholder: {
                            cardFallback
                        }
                    } else {
                        cardFallback
                    }
                }
                .frame(width: proxy.size.width, height: proxy.size.height)
                .clipped()
            }

            if inLane && card.exhausted {
                Color(hex: 0x111827).opacity(0.70)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(borderColor, lineWidth: 2)
        )
        .modifier(
            BoardCombatModifier(
                role: combatRole,
                motion: combatMotion,
                token: animationToken,
                cornerRadius: 12
            )
        )
        .overlay(alignment: .topLeading) {
            if let traitIcon = displayedTraitIcon {
                BadgeIcon(glyph: traitIcon, isLarge: isLarge)
                    .offset(x: -badgeOffset, y: -badgeOffset)
            }
        }
        .overlay(alignment: .topTrailing) {
            if !inLane, let cost = card.cost {
                BadgeText(text: "\(cost)", color: ArchetypeTheme.sky, isLarge: isLarge)
                    .offset(x: badgeOffset, y: -badgeOffset)
            }
        }
        .overlay(alignment: .bottomLeading) {
            if !card.isSpell {
                BadgeText(text: "\(card.attack)", color: ArchetypeTheme.red, isLarge: isLarge)
                    .offset(x: -badgeOffset, y: badgeOffset)
            }
        }
        .overlay(alignment: .bottomTrailing) {
            if !card.isSpell {
                BadgeText(text: "\(card.health)", color: ArchetypeTheme.green, isLarge: isLarge)
                    .offset(x: badgeOffset, y: badgeOffset)
            }
        }
        .opacity(inLane && card.hasStealth ? 0.72 : 1)
        .accessibilityLabel(card.shortName)
    }

    private var cardFallback: some View {
        RemoteImagePlaceholder()
    }
}

private struct BadgeText: View {
    let text: String
    let color: Color
    var isLarge = false

    var body: some View {
        Text(text)
            .font(.archetypeBody(isLarge ? 14 : 12, weight: isLarge ? .black : .semibold))
            .foregroundStyle(.white)
            .frame(width: isLarge ? 32 : 20, height: isLarge ? 32 : 20)
            .background(color)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color.black.opacity(0.85), lineWidth: 1))
    }
}

private struct BadgeIcon: View {
    let glyph: String
    var isLarge = false

    var body: some View {
        Text(glyph)
            .font(.system(size: isLarge ? 14 : 12, weight: isLarge ? .black : .regular))
            .frame(width: isLarge ? 32 : 20, height: isLarge ? 32 : 20)
            .background(Color.white)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color(hex: 0x111827), lineWidth: 1))
            .shadow(color: Color.black.opacity(0.28), radius: 4, x: 0, y: 2)
    }
}

private struct BoardCombatModifier: ViewModifier {
    let role: BoardCombatRole?
    let motion: BoardCombatMotion?
    let token: UUID?
    let cornerRadius: CGFloat

    func body(content: Content) -> some View {
        content
            .overlay {
                if let role {
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .stroke(role.borderColor, lineWidth: 3)
                        .shadow(color: role.borderColor.opacity(0.72), radius: 8, x: 0, y: 0)
                }
            }
            .animation(.spring(response: 0.28, dampingFraction: 0.72), value: role != nil)
            .modifier(BoardCombatMotionModifier(motion: motion, token: token))
    }
}

private struct BoardCombatMotionModifier: ViewModifier {
    enum Phase: CaseIterable {
        case idle
        case approach
        case peak
        case settle
    }

    struct Step {
        var offset: CGSize = .zero
        var scale: CGFloat = 1
        var brightness: Double = 0
    }

    let motion: BoardCombatMotion?
    let token: UUID?

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private static let idleToken = UUID()

    func body(content: Content) -> some View {
        content.phaseAnimator(
            Phase.allCases,
            trigger: token ?? Self.idleToken
        ) { view, phase in
            let step = step(for: phase)
            view
                .offset(x: step.offset.width, y: step.offset.height)
                .scaleEffect(step.scale)
                .brightness(step.brightness)
        } animation: { phase in
            .easeOut(duration: duration(entering: phase))
        }
    }

    private func step(for phase: Phase) -> Step {
        guard let motion, phase != .idle else {
            return Step()
        }

        let offset = reduceMotion
            ? CGVector.zero
            : motion.offset

        switch motion.kind {
        case .lunge:
            switch phase {
            case .approach:
                return Step(offset: scaled(offset, 0.4), scale: 1.03, brightness: 0.1)
            case .peak:
                return Step(offset: scaled(offset, 1), scale: 1.05, brightness: 0.18)
            case .settle:
                return Step(offset: scaled(offset, 0.3), scale: 1.02, brightness: 0.06)
            case .idle:
                return Step()
            }
        case .hit:
            switch phase {
            case .approach:
                return Step()
            case .peak:
                return Step(offset: scaled(offset, 1), scale: 0.97, brightness: 0.24)
            case .settle:
                return Step(offset: scaled(offset, -0.28), scale: 1.01, brightness: 0.08)
            case .idle:
                return Step()
            }
        case .healSource:
            switch phase {
            case .approach:
                return Step(offset: scaled(offset, 0.5), scale: 1.02, brightness: 0.08)
            case .peak:
                return Step(offset: scaled(offset, 1), scale: 1.03, brightness: 0.14)
            case .settle:
                return Step(offset: scaled(offset, 0.4), scale: 1.01, brightness: 0.05)
            case .idle:
                return Step()
            }
        case .healTarget:
            switch phase {
            case .approach:
                return Step(offset: CGSize(width: 0, height: reduceMotion ? 0 : -2), scale: 1.02, brightness: 0.08)
            case .peak:
                return Step(offset: CGSize(width: 0, height: reduceMotion ? 0 : -5), scale: 1.05, brightness: 0.18)
            case .settle:
                return Step(offset: CGSize(width: 0, height: reduceMotion ? 0 : -2), scale: 1.02, brightness: 0.06)
            case .idle:
                return Step()
            }
        case .spellTarget:
            switch phase {
            case .approach:
                return Step(offset: scaled(offset, 0.32), scale: 0.985, brightness: 0.12)
            case .peak:
                return Step(scale: 1.04, brightness: 0.22)
            case .settle:
                return Step(scale: 1.015, brightness: 0.08)
            case .idle:
                return Step()
            }
        }
    }

    private func duration(entering phase: Phase) -> TimeInterval {
        let kind = motion?.kind ?? .lunge

        switch phase {
        case .approach:
            switch kind {
            case .hit:
                return 0.22
            case .spellTarget:
                return 0.26
            default:
                return 0.18
            }
        case .peak:
            return kind == .spellTarget ? 0.12 : 0.15
        case .settle:
            return kind == .hit ? 0.1 : 0.13
        case .idle:
            return 0.15
        }
    }

    private func scaled(_ offset: CGVector, _ factor: CGFloat) -> CGSize {
        CGSize(width: offset.dx * factor, height: offset.dy * factor)
    }
}

private struct BoardPlayedSpellCardView: View {
    let playedSpell: BoardPlayedSpellCard
    let isBottomSide: Bool
    let point: CGPoint

    @State private var isVisible = false
    @State private var isHovering = false

    var body: some View {
        MiniGameCard(
            card: playedSpell.card,
            active: true,
            inLane: false,
            isLarge: true
        )
        .frame(width: 76, height: 106)
        .shadow(color: Color.black.opacity(0.42), radius: 18, x: 0, y: 12)
        .shadow(color: ArchetypeTheme.sky.opacity(0.26), radius: 18, x: 0, y: 0)
        .rotationEffect(.degrees(rotation))
        .rotationEffect(.degrees(isHovering ? 1 : -1))
        .scaleEffect(scale)
        .opacity(opacity)
        .offset(y: yOffset)
        .offset(y: isHovering ? -5 : 0)
        .position(point)
        .animation(.timingCurve(0.16, 0.84, 0.24, 1, duration: 0.28), value: isVisible)
        .animation(.timingCurve(0.4, 0, 0.2, 1, duration: 0.26), value: playedSpell.isLeaving)
        .onAppear {
            isVisible = true
            withAnimation(
                .easeInOut(duration: 1.3)
                    .repeatForever(autoreverses: true)
                    .delay(0.28)
            ) {
                isHovering = true
            }
        }
        .accessibilityHidden(true)
    }

    private var yOffset: CGFloat {
        if playedSpell.isLeaving {
            return isBottomSide ? -24 : 24
        }
        if isVisible {
            return isBottomSide ? -12 : 12
        }
        return isBottomSide ? 14 : -14
    }

    private var rotation: Double {
        if playedSpell.isLeaving {
            return isBottomSide ? -3 : 3
        }
        return isVisible ? 0 : (isBottomSide ? -3 : 3)
    }

    private var scale: CGFloat {
        if playedSpell.isLeaving {
            return 0.88
        }
        return isVisible ? 1 : 0.78
    }

    private var opacity: Double {
        if playedSpell.isLeaving {
            return 0
        }
        return isVisible ? 1 : 0
    }
}

private struct BoardCombatAnimationLayer: View {
    let combat: BoardTransientCombat
    let onBegin: (BoardTransientCombat) -> Void

    @State private var travelProgress: CGFloat = 0
    @State private var originExpanded = false
    @State private var originFaded = false
    @State private var trailFaded = false
    @State private var boltFaded = false
    @State private var impactVisible = false
    @State private var impactExpanded = false
    @State private var impactFaded = false

    private var distance: CGFloat {
        hypot(combat.target.x - combat.source.x, combat.target.y - combat.source.y)
    }

    private var isTraveling: Bool {
        distance >= 16
    }

    var body: some View {
        ZStack {
            CombatOriginFlash(kind: combat.kind, accent: combat.accent)
                .scaleEffect(originExpanded ? 1.35 : 0.3)
                .opacity(originFaded ? 0 : 0.96)
                .position(combat.source)

            if isTraveling {
                CombatTravelPath(
                    source: combat.source,
                    target: combat.target,
                    kind: combat.kind,
                    accent: combat.accent,
                    tip: combat.trailTip,
                    progress: travelProgress,
                    boltOpacity: boltFaded ? 0 : 1
                )
                .opacity(trailFaded ? 0 : 1)
            }

            CombatImpact(kind: combat.kind)
                .scaleEffect(impactExpanded ? 1.22 : 0.18)
                .opacity(impactVisible ? 1 : 0)
                .opacity(impactFaded ? 0 : 1)
                .position(combat.target)
        }
        .onAppear {
            onBegin(combat)

            withAnimation(.easeOut(duration: 0.62)) {
                originExpanded = true
            }
            withAnimation(.easeIn(duration: 0.44).delay(0.14)) {
                originFaded = true
            }

            withAnimation(.timingCurve(0.2, 0.82, 0.32, 1, duration: 0.62)) {
                travelProgress = 1
            }
            withAnimation(.easeIn(duration: 0.16).delay(0.44)) {
                boltFaded = true
            }
            withAnimation(.easeIn(duration: 0.24).delay(0.38)) {
                trailFaded = true
            }

            withAnimation(.easeOut(duration: 0.1).delay(0.26)) {
                impactVisible = true
            }
            withAnimation(.easeOut(duration: 0.36).delay(0.26)) {
                impactExpanded = true
            }
            withAnimation(.easeIn(duration: 0.22).delay(0.4)) {
                impactFaded = true
            }
        }
        .accessibilityHidden(true)
    }
}

private struct CombatOriginFlash: View {
    let kind: BoardCombatAnimationKind
    let accent: Color

    var body: some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [
                        Color.white.opacity(0.96),
                        accent.opacity(0.62),
                        accent.opacity(0),
                    ],
                    center: .center,
                    startRadius: 0,
                    endRadius: size / 2
                )
            )
            .frame(width: size, height: size)
            .blur(radius: 1)
    }

    private var size: CGFloat {
        switch kind {
        case .damage:
            return 28
        case .heal:
            return 30
        case .spellDamage:
            return 34
        }
    }
}

private struct CombatTravelPath: View {
    let source: CGPoint
    let target: CGPoint
    let kind: BoardCombatAnimationKind
    let accent: Color
    let tip: Color
    let progress: CGFloat
    let boltOpacity: Double

    private var currentPoint: CGPoint {
        CGPoint(
            x: source.x + ((target.x - source.x) * progress),
            y: source.y + ((target.y - source.y) * progress)
        )
    }

    var body: some View {
        ZStack {
            Path { path in
                path.move(to: source)
                path.addLine(to: target)
            }
            .trim(from: 0, to: progress)
            .stroke(
                LinearGradient(
                    colors: [
                        accent.opacity(0),
                        Color.white.opacity(0.9),
                        tip.opacity(0.72),
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                ),
                style: StrokeStyle(lineWidth: kind == .heal ? 4 : 3, lineCap: .round)
            )
            .shadow(color: accent.opacity(0.35), radius: 9, x: 0, y: 0)

            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            Color.white.opacity(0.96),
                            accent.opacity(0.88),
                            tip.opacity(0),
                        ],
                        center: .center,
                        startRadius: 1,
                        endRadius: 13
                    )
                )
                .frame(width: kind == .heal ? 20 : 24, height: kind == .heal ? 20 : 24)
                .opacity(boltOpacity)
                .position(currentPoint)
        }
    }
}

private struct CombatImpact: View {
    let kind: BoardCombatAnimationKind

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.white.opacity(0.68), lineWidth: 2)
                .frame(width: impactSize, height: impactSize)

            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            Color.white.opacity(0.78),
                            kind.impact.opacity(kind == .heal ? 0.3 : 0.24),
                            kind.impact.opacity(0),
                        ],
                        center: .center,
                        startRadius: 0,
                        endRadius: (impactSize + 18) / 2
                    )
                )
                .frame(width: impactSize + 18, height: impactSize + 18)
        }
    }

    private var impactSize: CGFloat {
        switch kind {
        case .damage:
            return 56
        case .heal:
            return 66
        case .spellDamage:
            return 72
        }
    }
}

private struct BoardValueBurstView: View {
    let burst: BoardValueBurst

    @State private var entered = false
    @State private var drifted = false
    @State private var faded = false

    var body: some View {
        Text(burst.text)
            .font(.archetypeBody(12, weight: .black))
            .foregroundStyle(.white)
            .padding(.horizontal, 10)
            .frame(height: 26)
            .background(
                burst.kind == .heal
                    ? ArchetypeTheme.green.opacity(0.86)
                    : Color(hex: 0x111827).opacity(0.9)
            )
            .clipShape(Capsule())
            .overlay(
                Capsule()
                    .stroke(burst.kind.accent.opacity(0.55), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.38), radius: 8, x: 0, y: 4)
            .shadow(color: burst.kind.accent.opacity(0.18), radius: 12, x: 0, y: 0)
            .scaleEffect(entered ? 1 : 0.72)
            .scaleEffect(faded ? 1.04 : 1)
            .opacity(entered ? 1 : 0)
            .opacity(faded ? 0 : 1)
            .offset(y: entered ? -10 : 0)
            .offset(y: drifted ? -14 : 0)
            .offset(y: faded ? -10 : 0)
            .position(x: burst.point.x, y: burst.point.y - 18)
            .onAppear {
                withAnimation(.easeOut(duration: 0.22)) {
                    entered = true
                }
                withAnimation(.easeOut(duration: 1.41).delay(0.22)) {
                    drifted = true
                }
                withAnimation(.easeIn(duration: 0.55).delay(1.63)) {
                    faded = true
                }
            }
            .accessibilityHidden(true)
    }
}

private struct GameOverlayFrame<Content: View>: View {
    let title: String
    let onDismiss: () -> Void
    let content: Content

    init(title: String, onDismiss: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.title = title
        self.onDismiss = onDismiss
        self.content = content()
    }

    var body: some View {
        ArchetypeScreen {
            GeometryReader { proxy in
                let topTitlePadding = min(proxy.safeAreaInsets.top, 46)

                VStack(spacing: 0) {
                    HStack(spacing: 0) {
                        Text(title)
                            .font(.archetypeBody(16, weight: .medium))
                            .foregroundStyle(ArchetypeTheme.muted)
                            .lineLimit(2)
                            .multilineTextAlignment(.center)
                            .padding(.top, topTitlePadding)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)

                        Button(action: onDismiss) {
                            Text("×")
                                .font(.system(size: 58, weight: .light))
                                .foregroundStyle(ArchetypeTheme.muted)
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                        }
                        .buttonStyle(.plain)
                        .frame(width: 96)
                        .overlay(alignment: .leading) {
                            Rectangle()
                                .fill(ArchetypeTheme.border)
                                .frame(width: 1)
                        }
                        .accessibilityLabel("Close overlay")
                    }
                    .frame(height: 96)
                    .overlay(alignment: .bottom) {
                        Rectangle()
                            .fill(ArchetypeTheme.border)
                            .frame(height: 1)
                    }

                    content
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .frame(maxWidth: 448)
                .frame(maxHeight: .infinity)
                .background(ArchetypeTheme.ink)
                .overlay(alignment: .leading) {
                    Rectangle()
                        .fill(ArchetypeTheme.border)
                        .frame(width: 1)
                }
                .overlay(alignment: .trailing) {
                    Rectangle()
                        .fill(ArchetypeTheme.border)
                        .frame(width: 1)
                }
                .ignoresSafeArea(.container, edges: .top)
            }
        }
    }
}

private struct EntityDetailSheet: View {
    let context: GameEntityDetailContext
    let playUnavailableReason: String?
    let attackUnavailableReason: String?
    let heroPowerUnavailableReason: String?
    let spellRequiresTarget: Bool
    let onPlayCard: (BoardCardSnapshot) -> Void
    let onAttack: (BoardCardSnapshot) -> Void
    let onUseHero: (GameSideSnapshot) -> Void
    let onDismiss: () -> Void

    private var title: String {
        switch context.kind {
        case .handCard:
            return "Card Details"
        case .ownCreature:
            return "Your Creature"
        case .opponentCreature:
            return "Enemy Creature"
        case .ownHero:
            return "Hero Power"
        case .opponentHero:
            return context.hero?.playerName ?? context.hero?.heroName ?? "Enemy Hero"
        }
    }

    private var displayName: String {
        context.card?.shortName ?? context.hero?.heroName ?? "Entity"
    }

    private var detail: String {
        if let card = context.card {
            return card.description.isEmpty ? "No description" : card.description
        }
        if let hero = context.hero {
            return hero.description.isEmpty ? "No description" : hero.description
        }
        return "No description"
    }

    private var cardIsInLane: Bool {
        switch context.kind {
        case .ownCreature, .opponentCreature:
            return true
        case .handCard, .ownHero, .opponentHero:
            return false
        }
    }

    var body: some View {
        GameOverlayFrame(title: title, onDismiss: onDismiss) {
            VStack(spacing: 0) {
                VStack {
                    if let card = context.card {
                        MiniGameCard(card: card, active: false, inLane: cardIsInLane, isLarge: true)
                            .frame(width: 184, height: 258)
                    } else if let hero = context.hero {
                        HeroDetailCard(hero: hero)
                            .frame(width: 184, height: 258)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding(.vertical, 20)

                VStack(spacing: 14) {
                    Text(displayName)
                        .font(.archetypeBody(18))
                        .foregroundStyle(ArchetypeTheme.text)
                        .multilineTextAlignment(.center)

                    Text(detail)
                        .font(.archetypeBody(16))
                        .foregroundStyle(ArchetypeTheme.text)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 18)
                .padding(.vertical, 18)
                .overlay(alignment: .top) {
                    Rectangle()
                        .fill(ArchetypeTheme.border)
                        .frame(height: 1)
                }

                actionArea
                    .padding(.horizontal, 16)
                    .padding(.vertical, 16)
                    .overlay(alignment: .top) {
                        Rectangle()
                            .fill(ArchetypeTheme.border)
                            .frame(height: 1)
                    }
            }
        }
    }

    @ViewBuilder
    private var actionArea: some View {
        VStack(spacing: 10) {
            switch context.kind {
            case .handCard:
                if let card = context.card {
                    Button {
                        onPlayCard(card)
                    } label: {
                        Text(playButtonTitle(for: card))
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(
                        FilledGameButtonStyle(
                            color: card.isSpell ? Color(hex: 0x9333EA) : Color(hex: 0x16A34A),
                            pressedColor: card.isSpell ? Color(hex: 0x7E22CE) : Color(hex: 0x15803D)
                        )
                    )
                    .disabled(playUnavailableReason != nil)
                    .opacity(playUnavailableReason == nil ? 1 : 0.55)

                    if let playUnavailableReason {
                        SheetNotice(text: playUnavailableReason, color: ArchetypeTheme.red)
                    }
                }
            case .ownCreature:
                if let card = context.card {
                    Button {
                        onAttack(card)
                    } label: {
                        Text("Attack")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(
                        FilledGameButtonStyle(
                            color: Color(hex: 0xDC2626),
                            pressedColor: Color(hex: 0xB91C1C)
                        )
                    )
                    .disabled(attackUnavailableReason != nil)
                    .opacity(attackUnavailableReason == nil ? 1 : 0.55)

                    if let attackUnavailableReason {
                        SheetNotice(text: attackUnavailableReason, color: ArchetypeTheme.red)
                    }
                }
            case .ownHero:
                if let hero = context.hero {
                    Button {
                        onUseHero(hero)
                    } label: {
                        Text(heroPowerLabel(hero))
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(
                        FilledGameButtonStyle(
                            color: Color(hex: 0x2563EB),
                            pressedColor: Color(hex: 0x1D4ED8)
                        )
                    )
                    .disabled(heroPowerUnavailableReason != nil)
                    .opacity(heroPowerUnavailableReason == nil ? 1 : 0.55)

                    if let heroPowerUnavailableReason {
                        SheetNotice(text: heroPowerUnavailableReason, color: ArchetypeTheme.red)
                    }
                }
            case .opponentCreature, .opponentHero:
                EmptyView()
            }

            Button(action: onDismiss) {
                Text("Close")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(
                FilledGameButtonStyle(
                    color: Color(hex: 0x4B5563),
                    pressedColor: Color(hex: 0x374151)
                )
            )
            .frame(maxWidth: .infinity)
        }
        .frame(maxWidth: .infinity)
    }

    private func heroPowerLabel(_ hero: GameSideSnapshot) -> String {
        guard hero.heroPowerCost > 0 else {
            return "Use Hero Power"
        }
        return "Use Hero Power (\(hero.heroPowerCost) Energy)"
    }

    private func playButtonTitle(for card: BoardCardSnapshot) -> String {
        guard card.isSpell else {
            return "Place on Board"
        }

        return spellRequiresTarget ? "Cast Spell (Select Target)" : "Cast Spell"
    }
}

private struct PlacementSheet: View {
    let context: GamePlacementContext
    let onSelectPosition: (Int) -> Void
    let onDismiss: () -> Void

    var body: some View {
        GameOverlayFrame(title: "Place Creature", onDismiss: onDismiss) {
            VStack(spacing: 0) {
                placementBand

                Text("Choose where to place this creature")
                    .font(.archetypeBody(16))
                    .foregroundStyle(ArchetypeTheme.text)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .overlay(alignment: .bottom) {
                        Rectangle()
                            .fill(ArchetypeTheme.border)
                            .frame(height: 1)
                    }

                VStack(spacing: 0) {
                    MiniGameCard(card: context.card, active: false, inLane: false, isLarge: true)
                        .frame(width: 184, height: 258)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                Spacer(minLength: 0)
            }
        }
    }

    private var placementBand: some View {
        GeometryReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Spacer(minLength: 0)

                    if context.boardCards.isEmpty {
                        PlacementZoneButton(position: 0, onSelectPosition: onSelectPosition)
                    } else {
                        PlacementZoneButton(position: 0, onSelectPosition: onSelectPosition)

                        ForEach(Array(context.boardCards.enumerated()), id: \.element.id) { index, card in
                            MiniGameCard(card: card, active: false, inLane: true)
                                .frame(width: 56, height: 78)
                            PlacementZoneButton(position: index + 1, onSelectPosition: onSelectPosition)
                        }
                    }

                    Spacer(minLength: 0)
                }
                .padding(.horizontal, 18)
                .frame(minWidth: proxy.size.width, minHeight: proxy.size.height)
            }
        }
        .frame(height: 160)
        .frame(maxWidth: .infinity)
        .background(ArchetypeTheme.panel2)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct PlacementZoneButton: View {
    let position: Int
    let onSelectPosition: (Int) -> Void

    var body: some View {
        Button {
            onSelectPosition(position)
        } label: {
            Image(systemName: "plus")
                .font(.system(size: 24, weight: .bold))
            .foregroundStyle(ArchetypeTheme.green)
            .frame(width: 64, height: 80)
            .background(ArchetypeTheme.green.opacity(0.13))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(
                        ArchetypeTheme.green.opacity(0.9),
                        style: StrokeStyle(lineWidth: 2, dash: [6, 4])
                    )
            )
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
    }
}

private struct TargetingSheet: View {
    let context: GameTargetingContext
    let options: [GameTargetOption]
    let onSelectTarget: (GameTargetOption) -> Void
    let onDismiss: () -> Void

    var body: some View {
        GameOverlayFrame(title: overlayTitle, onDismiss: onDismiss) {
            if let unavailableReason = context.unavailableReason {
                unavailableState(unavailableReason)
            } else {
                VStack(spacing: 0) {
                    targetBands
                    promptBand
                    sourceBand
                    sourceInfoBand
                }
            }
        }
    }

    private var overlayTitle: String {
        switch context.title {
        case "Cast Spell":
            return "Select Target"
        case "Select Attack Target":
            return "Attack"
        case "Use Hero Power":
            return "Hero Power"
        default:
            return context.title
        }
    }

    private var orderedTargetSides: [String] {
        var seen = Set<String>()
        var sides: [String] = []
        for option in options where !seen.contains(option.side) {
            seen.insert(option.side)
            sides.append(option.side)
        }
        return sides
    }

    private var enemySide: String? {
        switch context.scope {
        case .enemy, .any:
            return orderedTargetSides.first
        case .friendly:
            return nil
        }
    }

    private var friendlySide: String? {
        switch context.scope {
        case .friendly:
            return orderedTargetSides.first
        case .any:
            return orderedTargetSides.dropFirst().first
        case .enemy:
            return nil
        }
    }

    private var showsEnemyTargets: Bool {
        context.scope == .enemy || context.scope == .any
    }

    private var showsFriendlyTargets: Bool {
        context.scope == .friendly || context.scope == .any
    }

    @ViewBuilder
    private var targetBands: some View {
        if showsEnemyTargets {
            if let enemySide, let option = heroOption(for: enemySide) {
                TargetHeroBand(label: "Opponent", option: option, onSelectTarget: onSelectTarget)
            }

            if context.allowed.allowsCreature {
                TargetBoardBand(
                    options: creatureOptions(for: enemySide),
                    emptyText: "No enemy creatures",
                    onSelectTarget: onSelectTarget
                )
            }
        }

        if showsFriendlyTargets {
            if context.allowed.allowsCreature {
                TargetBoardBand(
                    options: creatureOptions(for: friendlySide),
                    emptyText: "No friendly creatures",
                    onSelectTarget: onSelectTarget
                )
            }

            if let friendlySide, let option = heroOption(for: friendlySide) {
                TargetHeroBand(label: "Your Hero", option: option, onSelectTarget: onSelectTarget)
            }
        }
    }

    private var promptBand: some View {
        Text(context.title)
            .font(.archetypeBody(16))
            .foregroundStyle(ArchetypeTheme.text)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .overlay(alignment: .top) {
                Rectangle()
                    .fill(ArchetypeTheme.border)
                    .frame(height: 1)
            }
            .overlay(alignment: .bottom) {
                Rectangle()
                    .fill(ArchetypeTheme.border)
                    .frame(height: 1)
            }
    }

    private var sourceBand: some View {
        VStack {
            if let sourceCard = context.sourceCard {
                MiniGameCard(
                    card: sourceCard,
                    active: false,
                    inLane: sourceCardIsInLane,
                    isLarge: true
                )
                    .frame(width: 184, height: 258)
                    .padding(.vertical, 20)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var sourceCardIsInLane: Bool {
        if case .attack = context.command {
            return true
        }
        return false
    }

    @ViewBuilder
    private var sourceInfoBand: some View {
        if let sourceCard = context.sourceCard {
            VStack(spacing: 14) {
                Text(sourceCard.shortName)
                    .font(.archetypeBody(18))
                    .foregroundStyle(ArchetypeTheme.text)
                    .multilineTextAlignment(.center)

                Text(sourceCard.description.isEmpty ? "No description" : sourceCard.description)
                    .font(.archetypeBody(16))
                    .foregroundStyle(ArchetypeTheme.text)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 18)
            .padding(.vertical, 18)
            .overlay(alignment: .top) {
                Rectangle()
                    .fill(ArchetypeTheme.border)
                    .frame(height: 1)
            }
        }
    }

    private func heroOption(for side: String?) -> GameTargetOption? {
        guard let side else {
            return nil
        }
        return options.first { $0.side == side && $0.hero != nil }
    }

    private func creatureOptions(for side: String?) -> [GameTargetOption] {
        guard let side else {
            return []
        }
        return options.filter { $0.side == side && $0.card != nil }
    }

    private func unavailableState(_ reason: String) -> some View {
        VStack(spacing: 8) {
            Spacer(minLength: 0)

            VStack(spacing: 10) {
                Text("Cannot Select Target")
                    .font(.archetypeBody(18))
                    .foregroundStyle(ArchetypeTheme.red)
                Text(reason)
                    .font(.archetypeBody(14))
                    .foregroundStyle(ArchetypeTheme.red.opacity(0.76))
                    .multilineTextAlignment(.center)
                Text("Tap to close")
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted.opacity(0.62))
                    .padding(.top, 8)
            }
            .padding(.horizontal, 24)

            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .contentShape(Rectangle())
        .onTapGesture(perform: onDismiss)
    }
}

private struct TargetHeroBand: View {
    let label: String
    let option: GameTargetOption
    let onSelectTarget: (GameTargetOption) -> Void

    var body: some View {
        Button {
            onSelectTarget(option)
        } label: {
            VStack(spacing: 5) {
                Text(label)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted)
                Text(option.title)
                    .font(.archetypeBody(17))
                    .foregroundStyle(ArchetypeTheme.text)
                Text(option.subtitle)
                    .font(.archetypeBody(15))
                    .foregroundStyle(ArchetypeTheme.text)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 96)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!option.enabled)
        .opacity(option.enabled ? 1 : 0.3)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct TargetBoardBand: View {
    let options: [GameTargetOption]
    let emptyText: String
    let onSelectTarget: (GameTargetOption) -> Void

    var body: some View {
        Group {
            if options.isEmpty {
                Text(emptyText)
                    .font(.archetypeBody(16))
                    .foregroundStyle(ArchetypeTheme.muted.opacity(0.72))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                GeometryReader { proxy in
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(alignment: .center, spacing: 9) {
                            Spacer(minLength: 0)

                            ForEach(options) { option in
                                Button {
                                    onSelectTarget(option)
                                } label: {
                                    if let card = option.card {
                                        MiniGameCard(card: card, active: false, inLane: true)
                                            .frame(width: 56, height: 78)
                                            .compositingGroup()
                                            .opacity(option.enabled ? 1 : 0.3)
                                    }
                                }
                                .buttonStyle(.plain)
                                .disabled(!option.enabled)
                            }

                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 18)
                        .frame(minWidth: proxy.size.width, minHeight: proxy.size.height)
                    }
                }
            }
        }
        .frame(height: 160)
        .frame(maxWidth: .infinity)
        .background(ArchetypeTheme.panel2)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)
        }
    }
}

private struct TargetOptionRow: View {
    let option: GameTargetOption

    var body: some View {
        HStack(spacing: 12) {
            if let card = option.card {
                MiniGameCard(card: card, active: option.enabled, inLane: true)
                    .frame(width: 48, height: 68)
            } else if let hero = option.hero {
                HeroDetailCard(hero: hero)
                    .frame(width: 48, height: 68)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(option.title)
                    .font(.archetypeBody(17, weight: .bold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
                Text(option.subtitle)
                    .font(.archetypeBody(12))
                    .foregroundStyle(ArchetypeTheme.muted)
            }

            Spacer()

            Image(systemName: option.enabled ? "target" : "nosign")
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(option.enabled ? ArchetypeTheme.gold2 : ArchetypeTheme.red)
        }
        .padding(12)
        .background(ArchetypeTheme.panelGradient)
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
    }
}

private struct MulliganOverlay: View {
    let cards: [BoardCardSnapshot]
    let isDone: Bool
    @Binding var selectedIds: Set<String>
    let onSubmit: () -> Void

    var body: some View {
        ZStack {
            Color.black.opacity(0.84)
                .ignoresSafeArea()

            ArchetypePanel {
                VStack(spacing: 16) {
                    VStack(spacing: 5) {
                        Text("Opening Hand")
                            .font(.archetypeBody(20, weight: .semibold))
                            .foregroundStyle(ArchetypeTheme.text)
                        Text(isDone ? "Waiting for opponent." : "Select cards to replace.")
                            .font(.archetypeBody(14))
                            .foregroundStyle(ArchetypeTheme.muted)
                    }

                    GeometryReader { geometry in
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 12) {
                                ForEach(cards) { card in
                                    Button {
                                        if !isDone {
                                            toggle(card)
                                        }
                                    } label: {
                                        MiniGameCard(
                                            card: card,
                                            active: selectedIds.contains(card.id),
                                            inLane: false
                                        )
                                    }
                                    .buttonStyle(.plain)
                                    .allowsHitTesting(!isDone)
                                    .frame(width: 76, height: 106)
                                }
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 8)
                            .frame(minWidth: geometry.size.width, alignment: .center)
                        }
                    }
                    .frame(height: 122)

                    if isDone {
                        SheetNotice(text: "Hand submitted.", color: ArchetypeTheme.green)
                    } else {
                        HStack(spacing: 14) {
                            Text("\(selectedIds.count) selected")
                                .font(.archetypeBody(14))
                                .foregroundStyle(ArchetypeTheme.muted)

                            Spacer(minLength: 0)

                            Button {
                                onSubmit()
                            } label: {
                                Text(selectedIds.isEmpty ? "Keep Hand" : "Replace Selected")
                            }
                            .buttonStyle(PrimaryGameButtonStyle())
                            .frame(width: selectedIds.isEmpty ? 118 : 170)
                        }
                    }
                }
            }
            .padding(.horizontal, 18)
        }
    }

    private func toggle(_ card: BoardCardSnapshot) {
        if selectedIds.contains(card.id) {
            selectedIds.remove(card.id)
        } else {
            selectedIds.insert(card.id)
        }
    }
}

private struct UpdatesSheet: View {
    let updates: [GameUpdateSnapshot]
    let viewerSide: String
    let heroName: (String) -> String
    let heroSnapshot: (String) -> GameSideSnapshot
    let updateCard: (GameUpdateSnapshot) -> BoardCardSnapshot?
    let updateEntity: (String?, String?, String) -> GameUpdateEntitySnapshot?
    let updateText: (GameUpdateSnapshot, Bool) -> String
    let onDismiss: () -> Void

    private static let bottomID = "updates-bottom"

    var body: some View {
        GameOverlayFrame(title: "Game Log", onDismiss: onDismiss) {
            ScrollViewReader { proxy in
                ScrollView {
                    if updates.isEmpty {
                        EmptyState(
                            title: "No Updates Yet",
                            detail: "Game events will appear here as the live socket receives them.",
                            systemImage: "text.bubble.fill"
                        )
                        .padding(18)
                    } else {
                        VStack(spacing: 0) {
                            ForEach(Array(groupedUpdates.enumerated()), id: \.element.id) { index, group in
                                VStack(spacing: 0) {
                                    Text(group.title.uppercased())
                                        .font(.archetypeBody(13, weight: .black))
                                        .tracking(1.2)
                                        .foregroundStyle(ArchetypeTheme.muted)
                                        .padding(.vertical, 11)
                                        .frame(maxWidth: .infinity)
                                        .background(Color.black.opacity(0.16))

                                    VStack(spacing: 8) {
                                        ForEach(group.updates) { update in
                                            UpdateLogRow(
                                                update: update,
                                                viewerSide: viewerSide,
                                                groupSide: group.side,
                                                hero: heroSnapshot(update.side),
                                                card: updateCard(update),
                                                sourceEntity: updateEntity(
                                                    update.value["source_type"]?.stringValue,
                                                    update.value["source_id"]?.stringValue,
                                                    update.side
                                                ),
                                                targetEntity: updateEntity(
                                                    update.value["target_type"]?.stringValue,
                                                    update.value["target_id"]?.stringValue,
                                                    update.side
                                                ),
                                                text: updateText(update, update.side == group.side)
                                            )
                                        }
                                    }
                                    .padding(.top, 16)
                                    .padding(.horizontal, 18)
                                    .padding(.bottom, 14)
                                }
                                .overlay(alignment: .bottom) {
                                    if index < groupedUpdates.count - 1 {
                                        Rectangle()
                                            .fill(ArchetypeTheme.border)
                                            .frame(height: 1)
                                    }
                                }
                            }
                        }
                    }

                    Color.clear
                        .frame(height: 1)
                        .id(Self.bottomID)
                }
                .onAppear {
                    scrollToBottom(proxy)
                }
                .onChange(of: updates.count) { _, _ in
                    scrollToBottom(proxy)
                }
            }
        }
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        DispatchQueue.main.async {
            proxy.scrollTo(Self.bottomID, anchor: .bottom)
        }
    }

    private var groupedUpdates: [UpdateGroup] {
        var groups: [UpdateGroup] = []
        var current: [GameUpdateSnapshot] = []
        var currentSide: String?

        for update in updates {
            if currentSide == nil {
                currentSide = update.side
            }
            current.append(update)

            if update.type == "update_end_turn" {
                groups.append(
                    UpdateGroup(
                        side: update.side,
                        index: groups.count + 1,
                        title: turnTitle(for: update.side, groupCount: groups.count),
                        updates: current
                    )
                )
                current = []
                currentSide = nil
            }
        }

        if !current.isEmpty {
            groups.append(
                UpdateGroup(
                    side: currentSide ?? current.first?.side ?? "",
                    index: groups.count + 1,
                    title: turnTitle(
                        for: currentSide ?? current.first?.side ?? "",
                        groupCount: groups.count
                    ),
                    updates: current
                )
            )
        }

        return groups
    }

    private func turnTitle(for side: String, groupCount: Int) -> String {
        let turnNumber = groupCount / 2 + 1
        let actor = side == viewerSide ? "You" : heroName(side)
        return "Turn \(turnNumber) - \(actor)"
    }
}

private struct UpdateLogRow: View {
    let update: GameUpdateSnapshot
    let viewerSide: String
    let groupSide: String
    let hero: GameSideSnapshot
    let card: BoardCardSnapshot?
    let sourceEntity: GameUpdateEntitySnapshot?
    let targetEntity: GameUpdateEntitySnapshot?
    let text: String

    var body: some View {
        HStack(spacing: 14) {
            switch update.type {
            case "update_draw_card":
                if update.side == viewerSide {
                    Text("Draw")
                    if let card {
                        UpdateCardThumb(card: card, borderColor: ArchetypeTheme.green)
                    }
                } else {
                    UpdateHeroThumb(hero: hero, borderColor: ArchetypeTheme.red)
                    Text("Draws a card")
                }
            case "update_play_card":
                Text("Play")
                if let card {
                    UpdateCardThumb(card: card, borderColor: borderColor)
                }
            case "update_damage":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "\(update.value["damage"]?.intValue ?? 0)",
                        glyph: "⚔️",
                        color: ArchetypeTheme.red
                    ),
                    targetBorderColor: targetBorderColor
                )
            case "update_heal":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "\(update.value["amount"]?.intValue ?? 0)",
                        glyph: "💚",
                        color: ArchetypeTheme.green
                    ),
                    targetBorderColor: ArchetypeTheme.green
                )
            case "update_buff":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "+\(update.value["amount"]?.intValue ?? 0) \(buffAttribute)",
                        glyph: "↑",
                        color: ArchetypeTheme.violet
                    ),
                    targetBorderColor: borderColor
                )
            case "update_remove":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "Remove",
                        glyph: "💀",
                        color: Color(hex: 0x4B5563)
                    ),
                    targetBorderColor: targetBorderColor
                )
            case "update_silence":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "Silence",
                        glyph: "🤫",
                        color: ArchetypeTheme.sky
                    ),
                    targetBorderColor: ArchetypeTheme.sky
                )
            case "update_summon":
                entityActionRow(
                    badge: UpdateActionBadge(
                        text: "Summon",
                        glyph: "✨",
                        color: ArchetypeTheme.violet
                    ),
                    targetBorderColor: borderColor
                )
            default:
                fallbackContent
            }
        }
        .font(.archetypeBody(16))
        .foregroundStyle(ArchetypeTheme.text)
        .frame(maxWidth: .infinity)
        .frame(minHeight: 48)
        .accessibilityLabel(text)
    }

    private var fallbackContent: some View {
        Text(text)
            .multilineTextAlignment(.center)
    }

    @ViewBuilder
    private func entityActionRow(
        badge: UpdateActionBadge,
        targetBorderColor: Color
    ) -> some View {
        if sourceEntity == nil && targetEntity == nil {
            fallbackContent
        } else {
            if let sourceEntity {
                UpdateEntityThumb(entity: sourceEntity, borderColor: borderColor)
            }

            badge

            if let targetEntity {
                UpdateEntityThumb(entity: targetEntity, borderColor: targetBorderColor)
            }
        }
    }

    private var borderColor: Color {
        update.side == viewerSide ? ArchetypeTheme.green : ArchetypeTheme.red
    }

    private var targetBorderColor: Color {
        update.side == viewerSide ? ArchetypeTheme.red : ArchetypeTheme.green
    }

    private var buffAttribute: String {
        let raw = update.value["attribute"]?.stringValue ?? ""
        return raw.isEmpty ? "stat" : raw
    }
}

private struct UpdateEntityThumb: View {
    let entity: GameUpdateEntitySnapshot
    let borderColor: Color

    var body: some View {
        switch entity {
        case .card(let card):
            UpdateCardThumb(card: card, borderColor: borderColor)
        case .hero(let hero):
            UpdateHeroThumb(hero: hero, borderColor: borderColor)
        }
    }
}

private struct UpdateActionBadge: View {
    let text: String
    let glyph: String
    let color: Color

    var body: some View {
        HStack(spacing: 7) {
            Text(glyph)
                .font(.system(size: 13, weight: .black))
            Text(text)
                .font(.archetypeBody(13, weight: .black))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
            Text("→")
                .font(.archetypeBody(10, weight: .black))
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 10)
        .frame(height: 30)
        .background(color)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .shadow(color: color.opacity(0.24), radius: 5, x: 0, y: 2)
    }
}

private struct UpdateHeroThumb: View {
    let hero: GameSideSnapshot
    let borderColor: Color

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(hex: 0xD1D5DB))

            if let heroArtURL = hero.heroArtURL {
                CachedRemoteImage(url: heroArtURL) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    fallback
                }
            } else {
                fallback
            }
        }
        .frame(width: 40, height: 56)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(borderColor, lineWidth: 2)
        )
        .accessibilityLabel(hero.heroName)
    }

    private var fallback: some View {
        RemoteImagePlaceholder()
    }
}

private struct UpdateGroup: Identifiable {
    let side: String
    let index: Int
    let title: String
    let updates: [GameUpdateSnapshot]

    var id: String {
        "\(index)-\(side)-\(updates.first?.id ?? "empty")"
    }

}

private struct UpdateGlyph: View {
    let type: String

    var body: some View {
        Image(systemName: systemImage)
            .font(.system(size: 14, weight: .black))
            .foregroundStyle(color)
            .frame(width: 32, height: 32)
            .background(color.opacity(0.14))
            .clipShape(Circle())
    }

    private var systemImage: String {
        switch type {
        case "update_damage":
            return "burst.fill"
        case "update_heal":
            return "cross.fill"
        case "update_buff":
            return "arrow.up.circle.fill"
        case "update_draw_card":
            return "rectangle.stack.fill"
        case "update_play_card":
            return "square.and.arrow.down.fill"
        case "update_summon":
            return "sparkles"
        case "update_remove":
            return "xmark.octagon.fill"
        case "update_silence":
            return "speaker.slash.fill"
        case "update_end_turn":
            return "forward.end.fill"
        default:
            return "circle.fill"
        }
    }

    private var color: Color {
        switch type {
        case "update_damage", "update_remove":
            return ArchetypeTheme.red
        case "update_heal":
            return ArchetypeTheme.green
        case "update_silence":
            return ArchetypeTheme.sky
        case "update_buff", "update_summon":
            return ArchetypeTheme.violet
        case "update_draw_card", "update_play_card":
            return ArchetypeTheme.sky
        case "update_end_turn":
            return ArchetypeTheme.gold2
        default:
            return ArchetypeTheme.muted
        }
    }
}

private struct GameOverOverlay: View {
    let title: String
    let winnerText: String
    let isVictory: Bool
    let eloChange: EloRatingChangeSnapshot?
    let isIntroGame: Bool
    let canRematch: Bool
    let isRematchLoading: Bool
    let isIntroRetryLoading: Bool
    let noticeText: String?
    let noticeColor: Color
    let onExit: () -> Void
    let onRematch: () -> Void
    let onIntroSignUp: () -> Void
    let onIntroRetry: () -> Void
    let onReturn: () -> Void

    var body: some View {
        ZStack {
            Color.black.opacity(0.75)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                VStack(spacing: 22) {
                    VStack(spacing: 14) {
                        Text(isVictory ? "🎉" : "💀")
                            .font(.system(size: 56))

                        Text(title)
                            .font(.archetypeBody(30, weight: .black))
                            .foregroundStyle(ArchetypeTheme.text)

                        if isIntroGame {
                            Text(introResultText)
                                .font(.archetypeBody(14))
                                .foregroundStyle(ArchetypeTheme.muted)
                                .multilineTextAlignment(.center)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    if let noticeText {
                        SheetNotice(text: noticeText, color: noticeColor)
                    }

                    if let eloChange {
                        RatingChangesPanel(eloChange: eloChange)
                    }

                    VStack(spacing: 10) {
                        if isIntroGame {
                            Button(action: isVictory ? onIntroSignUp : onIntroRetry) {
                                Text(introPrimaryActionText)
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(
                                FilledGameButtonStyle(
                                    color: Color(hex: 0x2563EB),
                                    pressedColor: Color(hex: 0x1D4ED8)
                                )
                            )
                            .disabled(isIntroRetryLoading)
                            .opacity(isIntroRetryLoading ? 0.65 : 1)
                        } else {
                            Button(action: onExit) {
                                Text("Exit Game")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(
                                FilledGameButtonStyle(
                                    color: Color(hex: 0x2563EB),
                                    pressedColor: Color(hex: 0x1D4ED8)
                                )
                            )
                        }

                        if !isIntroGame, canRematch {
                            Button(action: onRematch) {
                                Text(isRematchLoading ? "Creating..." : "Rematch")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(
                                FilledGameButtonStyle(
                                    color: ArchetypeTheme.green,
                                    pressedColor: Color(hex: 0x15803D)
                                )
                            )
                            .disabled(isRematchLoading)
                            .opacity(isRematchLoading ? 0.65 : 1)
                        }

                        if isIntroGame {
                            Button(action: onExit) {
                                Text("Exit Game")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(
                                FilledGameButtonStyle(
                                    color: Color(hex: 0x4B5563),
                                    pressedColor: Color(hex: 0x374151)
                                )
                            )
                        }

                        Button(action: onReturn) {
                            Text("Return to Game")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(
                            FilledGameButtonStyle(
                                color: Color(hex: 0x4B5563),
                                pressedColor: Color(hex: 0x374151)
                            )
                        )
                    }
                }
                .padding(28)
                .background(Color(hex: 0x1F2937))
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .shadow(color: Color.black.opacity(0.35), radius: 24, x: 0, y: 12)
            }
            .frame(maxWidth: 420)
            .padding(.horizontal, 32)
        }
    }

    private var introResultText: String {
        if isVictory {
            return "Create an account to keep playing Draw Two."
        }
        return "Try the intro match again with the same starting setup."
    }

    private var introPrimaryActionText: String {
        if isVictory {
            return "Create Account"
        }
        return isIntroRetryLoading ? "Starting..." : "Try Again"
    }
}

private struct RatingChangesPanel: View {
    let eloChange: EloRatingChangeSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("⚔️ Rating Changes")
                .font(.archetypeBody(18, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
                .frame(maxWidth: .infinity, alignment: .center)

            VStack(spacing: 8) {
                RatingChangeRow(change: eloChange.winner, color: ArchetypeTheme.green)
                RatingChangeRow(change: eloChange.loser, color: ArchetypeTheme.red)
            }
        }
        .padding(14)
        .background(Color(hex: 0x374151))
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private struct RatingChangeRow: View {
    let change: EloRatingPlayerChange
    let color: Color

    var body: some View {
        HStack(spacing: 10) {
            Text(change.displayName)
                .font(.archetypeBody(14, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
                .lineLimit(1)

            Spacer(minLength: 8)

            Text(verbatim: String(change.newRating))
                .font(.archetypeBody(15, weight: .black))
                .foregroundStyle(ArchetypeTheme.gold2)

            Text(verbatim: "[ \(formattedDelta) ]")
                .font(.archetypeBody(13, weight: .bold))
                .foregroundStyle(color)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(color.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }

    private var formattedDelta: String {
        change.change > 0 ? "+\(change.change)" : "\(change.change)"
    }
}

private struct GameMenuSheet: View {
    let latestUpdateText: String
    let nextGame: GameSummary?
    let canExtendTime: Bool
    let canConcede: Bool
    let onNextGame: (GameSummary) -> Void
    let onUpdates: () -> Void
    let onHowToPlay: () -> Void
    let onExtendTime: () -> Void
    let onConcede: () -> Void
    let onExit: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        GameOverlayFrame(title: "Menu", onDismiss: onDismiss) {
            VStack(spacing: 30) {
                if let nextGame {
                    GameMenuTextButton(
                        title: "Next Game",
                        color: ArchetypeTheme.sky,
                        action: { onNextGame(nextGame) }
                    )
                }

                GameMenuTextButton(title: "Log", color: ArchetypeTheme.text, action: onUpdates)

                GameMenuTextButton(title: "How to Play", color: ArchetypeTheme.text, action: onHowToPlay)

                if canExtendTime {
                    GameMenuTextButton(title: "Extend Time", color: ArchetypeTheme.text, action: onExtendTime)
                }

                if canConcede {
                    GameMenuTextButton(title: "Concede", color: ArchetypeTheme.text, action: onConcede)
                }

                GameMenuTextButton(title: "Exit Game", color: ArchetypeTheme.text, action: onExit)

                Spacer(minLength: 0)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.horizontal, 18)
            .padding(.top, 34)
            .padding(.bottom, 32)
        }
    }
}

private struct GameHowToPlaySheet: View {
    let onDismiss: () -> Void

    var body: some View {
        GameOverlayFrame(title: "How to Play", onDismiss: onDismiss) {
            ScrollView {
                HowToGuideContent(horizontalInset: 18)
                    .padding(.top, 28)
                    .padding(.bottom, 36)
            }
        }
    }
}

private struct GameMenuTextButton: View {
    let title: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.archetypeBody(24))
                .foregroundStyle(color)
                .frame(maxWidth: .infinity)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

private struct AutoSwitchGameOverlay: View {
    let gameName: String

    @State private var progress: CGFloat = 0

    var body: some View {
        ZStack {
            Color.black.opacity(0.55)
                .ignoresSafeArea()

            VStack(spacing: 12) {
                Text("Next game")
                    .font(.archetypeBody(13, weight: .bold))
                    .tracking(2.1)
                    .textCase(.uppercase)
                    .foregroundStyle(ArchetypeTheme.sky)

                Text(gameName)
                    .font(.archetypeBody(19, weight: .semibold))
                    .foregroundStyle(ArchetypeTheme.text)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)

                GeometryReader { proxy in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color(hex: 0x111827))

                        Rectangle()
                            .fill(ArchetypeTheme.sky)
                            .frame(width: max(0, proxy.size.width * progress))
                    }
                }
                .frame(height: 4)
            }
            .padding(.horizontal, 22)
            .padding(.vertical, 18)
            .frame(maxWidth: 320)
            .background(Color(hex: 0x111827).opacity(0.94))
            .overlay(
                RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius)
                    .stroke(ArchetypeTheme.sky.opacity(0.42), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.surfaceRadius))
            .shadow(color: Color.black.opacity(0.32), radius: 22, x: 0, y: 10)
        }
        .onAppear {
            progress = 0
            withAnimation(.linear(duration: 0.76)) {
                progress = 1
            }
        }
    }
}

private struct HeroDetailCard: View {
    let hero: GameSideSnapshot

    var body: some View {
        ZStack {
            if let heroArtURL = hero.heroArtURL {
                CachedRemoteImage(url: heroArtURL) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    heroFallback
                }
            } else {
                heroFallback
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
        .overlay(
            RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius)
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .overlay(alignment: .bottomTrailing) {
            BadgeText(text: hero.health.map(String.init) ?? "-", color: ArchetypeTheme.green, isLarge: true)
                .offset(x: 10, y: 10)
        }
    }

    private var heroFallback: some View {
        RemoteImagePlaceholder()
    }
}

private struct SheetNotice: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.archetypeBody(12))
            .foregroundStyle(color)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(color.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: ArchetypeTheme.controlRadius))
    }
}

private extension ISO8601DateFormatter {
    static let drawTwoWithFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [
            .withInternetDateTime,
            .withFractionalSeconds,
        ]
        return formatter
    }()

    static let drawTwoWithoutFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    static func drawTwoDate(from string: String) -> Date? {
        drawTwoWithFractionalSeconds.date(from: string)
            ?? drawTwoWithoutFractionalSeconds.date(from: string)
    }
}

private extension BoardCardSnapshot {
    func hasTrait(_ type: String) -> Bool {
        traits.contains { trait in
            trait["type"]?.stringValue == type || trait["slug"]?.stringValue == type
        }
    }
}

private extension String {
    var displayNameFromSlug: String {
        replacingOccurrences(of: "_", with: " ")
            .split(separator: " ")
            .map { word in
                word.prefix(1).uppercased() + word.dropFirst()
            }
            .joined(separator: " ")
    }
}
