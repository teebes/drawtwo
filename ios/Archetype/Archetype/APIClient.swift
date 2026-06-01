import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case unauthorized
    case server(status: Int, message: String)
    case emptyResponse
    case decodingFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The backend URL could not be built."
        case .unauthorized:
            return "Your session has expired."
        case .server(let status, let message):
            return "Backend returned \(status): \(message)"
        case .emptyResponse:
            return "The backend returned an empty response."
        case .decodingFailed(let message):
            return "Could not read the backend response: \(message)"
        }
    }
}

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(session: URLSession = .shared) {
        self.session = session

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .useDefaultKeys
        self.encoder = encoder
    }

    func get<Response: Decodable>(
        _ path: String,
        accessToken: String? = nil
    ) async throws -> Response {
        try await request(
            method: "GET",
            path: path,
            queryItems: [],
            body: nil,
            accessToken: accessToken
        )
    }

    func get<Response: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem],
        accessToken: String? = nil
    ) async throws -> Response {
        try await request(
            method: "GET",
            path: path,
            queryItems: queryItems,
            body: nil,
            accessToken: accessToken
        )
    }

    func post<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body,
        accessToken: String? = nil
    ) async throws -> Response {
        try await post(path, queryItems: [], body: body, accessToken: accessToken)
    }

    func post<Body: Encodable, Response: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem],
        body: Body,
        accessToken: String? = nil
    ) async throws -> Response {
        let data = try encoder.encode(body)
        return try await request(
            method: "POST",
            path: path,
            queryItems: queryItems,
            body: data,
            accessToken: accessToken
        )
    }

    func put<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body,
        accessToken: String? = nil
    ) async throws -> Response {
        let data = try encoder.encode(body)
        return try await request(
            method: "PUT",
            path: path,
            queryItems: [],
            body: data,
            accessToken: accessToken
        )
    }

    func patch<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body,
        accessToken: String? = nil
    ) async throws -> Response {
        let data = try encoder.encode(body)
        return try await request(
            method: "PATCH",
            path: path,
            queryItems: [],
            body: data,
            accessToken: accessToken
        )
    }

    func delete<Response: Decodable>(
        _ path: String,
        accessToken: String? = nil
    ) async throws -> Response {
        try await request(
            method: "DELETE",
            path: path,
            queryItems: [],
            body: nil,
            accessToken: accessToken
        )
    }

    private func request<Response: Decodable>(
        method: String,
        path: String,
        queryItems: [URLQueryItem],
        body: Data?,
        accessToken: String?
    ) async throws -> Response {
        let url = try makeURL(path, queryItems: queryItems)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("Archetype-iOS/0.1", forHTTPHeaderField: "User-Agent")

        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        if let accessToken {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.server(status: -1, message: "Missing HTTP response")
        }

        if httpResponse.statusCode == 401 {
            throw APIError.unauthorized
        }

        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.server(
                status: httpResponse.statusCode,
                message: Self.serverMessage(from: data)
            )
        }

        guard !data.isEmpty else {
            if let emptyResponse = EmptyResponse() as? Response {
                return emptyResponse
            }
            throw APIError.emptyResponse
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decodingFailed(error.localizedDescription)
        }
    }

    private func makeURL(_ path: String, queryItems: [URLQueryItem]) throws -> URL {
        let normalizedPath = path.hasPrefix("/") ? path : "/\(path)"
        var components = URLComponents(
            url: AppConfig.apiBaseURL,
            resolvingAgainstBaseURL: false
        )
        components?.path = AppConfig.apiBaseURL.path + normalizedPath
        if !queryItems.isEmpty {
            components?.queryItems = queryItems
        }

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        return url
    }

    private static func serverMessage(from data: Data) -> String {
        guard !data.isEmpty else {
            return "No response body"
        }

        if
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let directMessage = object["error"] ?? object["message"] ?? object["detail"]
        {
            return formattedMessage(directMessage)
        }

        if let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            let fieldErrors = object
                .sorted { $0.key < $1.key }
                .compactMap { key, value in
                    fieldMessage(key: key, value: value)
                }

            if !fieldErrors.isEmpty {
                return fieldErrors.joined(separator: " ")
            }
        }

        return String(data: data, encoding: .utf8) ?? "Unparseable response"
    }

    private static func fieldMessage(key: String, value: Any) -> String? {
        let message = formattedMessage(value)
        guard !message.isEmpty else {
            return nil
        }

        if key == "non_field_errors" {
            return message
        }

        return "\(key): \(message)"
    }

    private static func formattedMessage(_ value: Any) -> String {
        if let messages = value as? [String] {
            return messages.joined(separator: " ")
        }

        if let messages = value as? [Any] {
            return messages.map { formattedMessage($0) }.joined(separator: " ")
        }

        return String(describing: value)
    }
}
