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
}

struct AuthResponse: Decodable {
    let access: String?
    let refresh: String?
    let accessToken: String?
    let refreshToken: String?
    let user: User?

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

struct PasswordlessLoginRequest: Encodable {
    let email: String
}

struct EmailConfirmationRequest: Encodable {
    let key: String
}

struct LoginLinkResponse: Decodable {
    let message: String?
    let email: String?
}

struct Title: Codable, Identifiable, Equatable {
    let id: Int
    let slug: String
    let name: String
    let description: String?
    let artUrl: String?
    let status: String?
    let canEdit: Bool?
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

struct TitleSummary: Decodable, Equatable {
    let id: Int
    let slug: String
    let name: String
}

struct GameSummary: Codable, Identifiable, Equatable {
    let id: Int
    let name: String
    let type: String
    let isUserTurn: Bool
}

struct GameListResponse: Decodable {
    let games: [GameSummary]
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

struct EmptyBody: Encodable {}

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

    var prettyPrinted: String {
        guard
            let data = try? JSONEncoder().encode(self),
            let object = try? JSONSerialization.jsonObject(with: data),
            let prettyData = try? JSONSerialization.data(
                withJSONObject: object,
                options: [.prettyPrinted, .sortedKeys]
            ),
            let string = String(data: prettyData, encoding: .utf8)
        else {
            return description
        }
        return string
    }
}
