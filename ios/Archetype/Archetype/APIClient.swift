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
        try await request(method: "GET", path: path, body: nil, accessToken: accessToken)
    }

    func post<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body,
        accessToken: String? = nil
    ) async throws -> Response {
        let data = try encoder.encode(body)
        return try await request(
            method: "POST",
            path: path,
            body: data,
            accessToken: accessToken
        )
    }

    private func request<Response: Decodable>(
        method: String,
        path: String,
        body: Data?,
        accessToken: String?
    ) async throws -> Response {
        let url = try makeURL(path)
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
            throw APIError.emptyResponse
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decodingFailed(error.localizedDescription)
        }
    }

    private func makeURL(_ path: String) throws -> URL {
        let normalizedPath = path.hasPrefix("/") ? path : "/\(path)"
        var components = URLComponents(
            url: AppConfig.apiBaseURL,
            resolvingAgainstBaseURL: false
        )
        components?.path = AppConfig.apiBaseURL.path + normalizedPath

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
            return String(describing: directMessage)
        }

        return String(data: data, encoding: .utf8) ?? "Unparseable response"
    }
}
