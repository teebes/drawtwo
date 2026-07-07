import Foundation

struct User: Codable, Identifiable, Equatable {
    let id: Int
    let email: String
    let username: String?
    let displayName: String?
    let avatar: String?
    let isEmailVerified: Bool?
    let isStaff: Bool?
    let status: String?
    let appleConnected: Bool?
    let googleConnected: Bool?
    let createdAt: String?
    let updatedAt: String?
}

struct AuthResponse: Decodable {
    let message: String?
    let access: String?
    let refresh: String?
    let accessToken: String?
    let refreshToken: String?
    let user: User?
    let requiresApproval: Bool?

    var resolvedAccessToken: String? {
        access ?? accessToken
    }

    var resolvedRefreshToken: String? {
        refresh ?? refreshToken
    }
}

struct TokenRefreshResponse: Decodable {
    let access: String
    let refresh: String?
}

struct LogoutRequest: Encodable {
    let refresh: String
}

struct ProfileUpdateRequest: Encodable {
    let username: String
}

struct PasswordlessLoginRequest: Encodable {
    let email: String
    let client = "ios"
}

struct PasswordSignInRequest: Encodable {
    let email: String
    let password: String
}

struct EmailConfirmationRequest: Encodable {
    let key: String
}

struct GoogleNativeSignInRequest: Encodable {
    let idToken: String

    enum CodingKeys: String, CodingKey {
        case idToken = "id_token"
    }
}

struct AppleSignInRequest: Encodable {
    let identityToken: String
    let authorizationCode: String?

    enum CodingKeys: String, CodingKey {
        case identityToken = "identity_token"
        case authorizationCode = "authorization_code"
    }
}

struct LoginLinkResponse: Decodable {
    let message: String?
    let email: String?
}

struct RegistrationRequest: Encodable {
    let email: String
    let username: String?
}

struct RegistrationResponse: Decodable {
    let message: String?
    let user: User?
    let requiresApproval: Bool?
}

struct Title: Codable, Identifiable, Equatable {
    let id: Int
    let slug: String
    let name: String
    let description: String?
    let artUrl: String?
    let status: String?
    let canEdit: Bool?

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.titleBannerURL
    }
}

struct Hero: Codable, Identifiable, Equatable {
    let id: Int
    let slug: String?
    let name: String
    let health: Int?
    let artUrl: String?
    let faction: String?
    let heroPower: JSONValue?
    let spec: JSONValue?

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.heroArtURL(slug: slug)
    }
}

struct Deck: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    let description: String?
    let hero: Hero
    let cardCount: Int?
    let createdAt: String?
    let updatedAt: String?
}

struct DeckListResponse: Decodable {
    let title: TitleSummary
    let decks: [Deck]
    let count: Int
    let lastUsedDeckId: Int?
    let lastUsedFriendId: Int?
}

struct TitleSummary: Codable, Equatable {
    let id: Int
    let slug: String
    let name: String
}

struct GameSummary: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    let type: String
    let ladderType: LadderType?
    let isUserTurn: Bool
}

struct GameListResponse: Decodable {
    let games: [GameSummary]
}

struct IntroScenarioStartResponse: Decodable, Hashable {
    let id: Int
    let status: String?
    let gameType: String
    let titleSlug: String
    let viewerSide: String
    let accessToken: String
    let message: String?
}

enum LadderType: String, CaseIterable, Identifiable, Codable {
    case rapid
    case daily

    var id: String {
        rawValue
    }

    var label: String {
        switch self {
        case .rapid:
            return "Rapid"
        case .daily:
            return "Daily"
        }
    }
}

struct LeaderboardPlayer: Codable, Identifiable, Equatable {
    let id: Int
    let username: String?
    let displayName: String
    let avatar: String?
    let eloRating: Int
    let wins: Int
    let losses: Int
    let totalGames: Int
}

struct FriendUser: Codable, Identifiable, Equatable {
    let id: Int
    let username: String?
    let displayName: String?
    let avatar: String?

    var displayLabel: String {
        displayName?.isEmpty == false ? displayName! : username ?? "Player \(id)"
    }

    var usernameLabel: String? {
        guard let username, !username.isEmpty else {
            return nil
        }
        return "@\(username)"
    }
}

enum FriendshipStatus: String, Codable {
    case pending
    case accepted
    case declined
    case blocked
}

struct Friendship: Codable, Identifiable, Equatable {
    let id: Int
    let friend: Int
    let friendData: FriendUser
    let status: FriendshipStatus
    let isInitiator: Bool
    let createdAt: String?
    let updatedAt: String?
}

struct FriendRequest: Encodable {
    let username: String
}

struct FriendshipActionRequest: Encodable {
    let action: String
}

enum GameMode: String, CaseIterable, Identifiable {
    case pvp
    case pve

    var id: String {
        rawValue
    }

    var label: String {
        switch self {
        case .pvp:
            return "vs Player"
        case .pve:
            return "vs AI"
        }
    }
}

struct RankedQueueRequest: Encodable {
    let deckId: Int
    let ladderType: LadderType

    enum CodingKeys: String, CodingKey {
        case deckId = "deck_id"
        case ladderType = "ladder_type"
    }
}

struct RankedQueueTitle: Codable, Equatable {
    let id: Int?
    let slug: String
    let name: String
}

struct RankedQueueDeck: Codable, Equatable {
    let id: Int
    let name: String
    let hero: String
}

struct RankedQueueEntry: Codable, Identifiable, Equatable {
    let id: Int
    let status: String
    let title: RankedQueueTitle?
    let deck: RankedQueueDeck
    let eloRating: Int
    let ladderType: LadderType
    let message: String?
    let queuedAt: String?
}

struct RankedQueueStatusResponse: Decodable {
    let inQueue: Bool
    let queueEntry: RankedQueueEntry?
    let error: String?
}

struct TitleNotification: Codable, Identifiable, Equatable {
    let refId: Int
    let type: String
    let message: String
    let isUserTurn: Bool?

    var id: String {
        "\(type)-\(refId)"
    }

    var isGameNotification: Bool {
        switch type {
        case "game_ranked", "game_friendly", "game_pve", "game_ended":
            return true
        default:
            return false
        }
    }

    var countsTowardAppBadge: Bool {
        switch type {
        case "game_challenge", "friend_request":
            return true
        case "game_ranked", "game_friendly":
            return isUserTurn == true
        default:
            return false
        }
    }

    var emoji: String {
        switch type {
        case "game_ranked", "game_ranked_queued":
            return "⚔️"
        case "game_friendly", "game_challenge":
            return "🤝"
        case "friend_request":
            return "👥"
        case "game_pve":
            return "👾"
        case "game_ended":
            return "🏁"
        default:
            return "🔔"
        }
    }
}

struct ChallengeAcceptRequest: Encodable {
    let challengeeDeckId: Int

    enum CodingKeys: String, CodingKey {
        case challengeeDeckId = "challengee_deck_id"
    }
}

struct ChallengeAcceptResponse: Decodable {
    let gameId: Int
}

enum FriendlyChallengeStatus: String, Codable {
    case pending
    case accepted
    case cancelled
    case expired
}

struct FriendlyChallengeUser: Codable, Identifiable, Equatable {
    let id: Int
    let displayName: String
}

struct FriendlyChallengeDeck: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    let hero: String
}

struct FriendlyChallenge: Codable, Identifiable, Equatable {
    let id: Int
    let status: FriendlyChallengeStatus
    let title: TitleSummary?
    let challenger: FriendlyChallengeUser
    let challengee: FriendlyChallengeUser
    let challengerDeck: FriendlyChallengeDeck
}

struct PendingChallengesResponse: Decodable, Equatable {
    let incoming: [FriendlyChallenge]
    let outgoing: [FriendlyChallenge]
}

struct FriendlyChallengeCreateRequest: Encodable {
    let titleSlug: String
    let challengeeUserId: Int
    let challengerDeckId: Int

    enum CodingKeys: String, CodingKey {
        case titleSlug = "title_slug"
        case challengeeUserId = "challengee_user_id"
        case challengerDeckId = "challenger_deck_id"
    }
}

struct ChallengeActionResponse: Decodable {
    let success: Bool?
    let message: String?
}

enum CardTypeFilter: String, CaseIterable, Identifiable {
    case all
    case creature
    case spell

    var id: String {
        rawValue
    }

    var label: String {
        switch self {
        case .all:
            return "All"
        case .creature:
            return "Creatures"
        case .spell:
            return "Spells"
        }
    }
}

struct CardTemplate: Codable, Identifiable, Equatable {
    let id: Int
    let type: String?
    let slug: String
    let name: String
    let description: String?
    let cardType: String
    let cost: Int
    let attack: Int
    let health: Int
    let traits: [JSONValue]
    let faction: String?
    let artUrl: String?
    let isCollectible: Bool?
    let heroSlugs: [String]?

    var isSpell: Bool {
        cardType == "spell"
    }

    var isCollectibleCard: Bool {
        isCollectible != false
    }

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.cardArtURL(slug: slug)
    }

    var traitTypes: [String] {
        traits.compactMap { trait in
            trait["type"]?.stringValue ?? trait["slug"]?.stringValue
        }
    }

    var primaryTrait: String? {
        let priority = ["stealth", "taunt", "deathrattle", "battlecry", "ranged", "charge", "unique"]
        return priority.first { traitTypes.contains($0) }
    }
}

struct GameHistoryResponse: Decodable {
    let stats: GameHistoryStats
    let games: [GameHistoryItem]
    let pagination: GameHistoryPagination
}

struct GameHistoryStats: Decodable, Equatable {
    let ranked: GameHistoryRankedStats
    let friendly: GameHistoryFriendlyStats
    let currentRating: Int?
    let ladderType: LadderType?
}

struct GameHistoryRankedStats: Decodable, Equatable {
    let total: Int
    let wins: Int
    let losses: Int
}

struct GameHistoryFriendlyStats: Decodable, Equatable {
    let total: Int
}

struct GameHistoryItem: Codable, Identifiable, Equatable {
    let id: Int
    let type: String
    let ladderType: LadderType?
    let status: String
    let opponentName: String
    let opponentHero: String?
    let userHero: String?
    let outcome: String?
    let isUserTurn: Bool?
    let eloChange: Int?
    let createdAt: String
    let updatedAt: String?
}

struct GameHistoryPagination: Decodable, Equatable {
    let page: Int
    let totalPages: Int
    let totalGames: Int
    let hasNext: Bool
    let hasPrevious: Bool
}

struct DeckConfig: Codable, Equatable {
    let deckSizeLimit: Int
    let minCardsInDeck: Int
    let deckCardMaxCount: Int
}

struct DeckDetailTitle: Codable, Equatable {
    let id: Int
    let slug: String
    let name: String
}

struct DeckDetailHero: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    let slug: String
    let health: Int
    let artUrl: String?

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.heroArtURL(slug: slug)
    }
}

struct DeckCard: Codable, Identifiable, Equatable {
    let id: Int
    let type: String?
    let slug: String
    let name: String
    let description: String?
    let cardType: String
    let cost: Int
    let attack: Int
    let health: Int
    let traits: [JSONValue]
    let faction: String?
    let artUrl: String?
    let isCollectible: Bool?
    let heroSlugs: [String]?
    var count: Int

    var isSpell: Bool {
        cardType == "spell"
    }

    var resolvedArtUrl: String? {
        if let artUrl, !artUrl.isEmpty {
            return artUrl
        }

        return AppConfig.cardArtURL(slug: slug)
    }

    var traitTypes: [String] {
        traits.compactMap { trait in
            trait["type"]?.stringValue ?? trait["slug"]?.stringValue
        }
    }

    var isUnique: Bool {
        traitTypes.contains("unique")
    }
}

struct DeckDetail: Codable, Identifiable, Equatable {
    let id: Int
    var name: String
    var description: String?
    let title: DeckDetailTitle
    var hero: DeckDetailHero
    let config: DeckConfig
    var cards: [DeckCard]
    let allCards: [CardTemplate]?
    var totalCards: Int
    let createdAt: String?
    var updatedAt: String?
}

struct DeckSaveRequest: Encodable {
    let name: String
    let description: String
    let heroId: Int

    enum CodingKeys: String, CodingKey {
        case name
        case description
        case heroId = "hero_id"
    }
}

struct DeckSaveResponse: Decodable {
    let id: Int
    let message: String?
}

struct DeckArchiveResponse: Decodable {
    let message: String?
    let titleSlug: String?
}

struct DeckCardAddRequest: Encodable {
    let cardSlug: String
    let count: Int

    enum CodingKeys: String, CodingKey {
        case cardSlug = "card_slug"
        case count
    }
}

struct DeckCardCountRequest: Encodable {
    let count: Int
}

struct DeckCardMutationResponse: Decodable {
    let id: Int?
    let name: String?
    let count: Int?
    let message: String?
}

struct CreateGameRequest: Encodable {
    let playerDeckId: Int
    let aiDeckId: Int?
    let opponentDeckId: Int?

    enum CodingKeys: String, CodingKey {
        case playerDeckId = "player_deck_id"
        case aiDeckId = "ai_deck_id"
        case opponentDeckId = "opponent_deck_id"
    }
}

struct CreateGameResponse: Decodable {
    let id: Int
    let status: String
    let gameType: String?
    let message: String?
}

struct RematchResponse: Decodable {
    let id: Int
    let status: String
    let titleSlug: String?
}

struct PushDeviceRegistrationRequest: Encodable {
    let token: String
    let platform: String
    let bundleId: String
    let environment: String

    enum CodingKeys: String, CodingKey {
        case token
        case platform
        case bundleId = "bundle_id"
        case environment
    }
}

struct PushDeviceRegistrationResponse: Decodable {
    let id: Int
    let platform: String
    let environment: String
    let bundleId: String
    let isActive: Bool
}

struct PushDeviceDeactivationRequest: Encodable {
    let token: String
    let bundleId: String
    let environment: String

    enum CodingKeys: String, CodingKey {
        case token
        case bundleId = "bundle_id"
        case environment
    }
}

struct PushDeviceDeactivationResponse: Decodable {
    let deactivated: Int
}

struct EmptyBody: Encodable {}
struct EmptyResponse: Decodable, Equatable {}

enum JSONValue: Codable, Hashable, CustomStringConvertible {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
        } else if let bool = try? container.decode(Bool.self) {
            self = .bool(bool)
        } else if let int = try? container.decode(Int.self) {
            self = .number(Double(int))
        } else if let double = try? container.decode(Double.self) {
            self = .number(double)
        } else if let string = try? container.decode(String.self) {
            self = .string(string)
        } else if let array = try? container.decode([JSONValue].self) {
            self = .array(array)
        } else if let object = try? container.decode([String: JSONValue].self) {
            self = .object(object)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unsupported JSON value"
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }

    var description: String {
        switch self {
        case .string(let value):
            return value
        case .number(let value):
            if value.rounded() == value {
                return String(Int(value))
            }
            return String(value)
        case .bool(let value):
            return value ? "true" : "false"
        case .object(let value):
            return "{\(value.keys.sorted().joined(separator: ", "))}"
        case .array(let value):
            return "\(value.count) items"
        case .null:
            return "null"
        }
    }

    subscript(key: String) -> JSONValue? {
        if case .object(let object) = self {
            return object[key]
        }
        return nil
    }

    var stringValue: String? {
        if case .string(let value) = self {
            return value
        }
        return nil
    }

    var intValue: Int? {
        if case .number(let value) = self {
            return Int(value)
        }
        return nil
    }

    var boolValue: Bool? {
        if case .bool(let value) = self {
            return value
        }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case .array(let value) = self {
            return value
        }
        return nil
    }

    var objectValue: [String: JSONValue]? {
        if case .object(let value) = self {
            return value
        }
        return nil
    }
}
