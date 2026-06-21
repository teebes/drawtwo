import CryptoKit
import Foundation
import SwiftUI
import UIKit

final class RemoteImageCache: @unchecked Sendable {
    static let shared = RemoteImageCache()

    private let memoryCache = NSCache<NSURL, UIImage>()
    private let lock = NSLock()
    private let cacheDirectory: URL
    private var tasks: [URL: Task<UIImage, Error>] = [:]

    private init() {
        let baseDirectory = FileManager.default.urls(
            for: .cachesDirectory,
            in: .userDomainMask
        ).first ?? FileManager.default.temporaryDirectory

        cacheDirectory = baseDirectory.appendingPathComponent(
            "RemoteImageCache",
            isDirectory: true
        )
        try? FileManager.default.createDirectory(
            at: cacheDirectory,
            withIntermediateDirectories: true
        )

        memoryCache.countLimit = 350
        memoryCache.totalCostLimit = 90 * 1024 * 1024
    }

    func cachedImage(for url: URL) -> UIImage? {
        memoryCache.object(forKey: url as NSURL)
    }

    func image(for url: URL) async throws -> UIImage {
        if let cachedImage = cachedImage(for: url) {
            return cachedImage
        }

        let task = existingOrNewTask(for: url)

        do {
            let image = try await task.value
            memoryCache.setObject(image, forKey: url as NSURL, cost: image.memoryCost)
            removeTask(for: url)
            return image
        } catch {
            removeTask(for: url)
            throw error
        }
    }

    func prefetch(_ urls: [URL]) {
        let uniqueURLs = Array(Set(urls))
        guard !uniqueURLs.isEmpty else {
            return
        }

        Task(priority: .utility) {
            await withTaskGroup(of: Void.self) { group in
                var iterator = uniqueURLs.makeIterator()
                let workerCount = min(6, uniqueURLs.count)

                for _ in 0..<workerCount {
                    guard let url = iterator.next() else {
                        break
                    }
                    group.addTask { [self] in
                        _ = try? await image(for: url)
                    }
                }

                while await group.next() != nil {
                    guard let url = iterator.next() else {
                        continue
                    }
                    group.addTask { [self] in
                        _ = try? await image(for: url)
                    }
                }
            }
        }
    }

    private func existingOrNewTask(for url: URL) -> Task<UIImage, Error> {
        lock.lock()
        defer { lock.unlock() }

        if let task = tasks[url] {
            return task
        }

        let cacheDirectory = cacheDirectory
        let task = Task.detached(priority: .utility) {
            try await Self.loadImage(for: url, cacheDirectory: cacheDirectory)
        }
        tasks[url] = task
        return task
    }

    private func removeTask(for url: URL) {
        lock.lock()
        tasks[url] = nil
        lock.unlock()
    }

    private static func loadImage(for url: URL, cacheDirectory: URL) async throws -> UIImage {
        let fileURL = cacheFileURL(for: url, in: cacheDirectory)

        if let data = try? Data(contentsOf: fileURL),
           let image = UIImage(data: data) {
            return image
        }

        var request = URLRequest(url: url)
        request.cachePolicy = .returnCacheDataElseLoad
        request.timeoutInterval = 30

        let (data, response) = try await URLSession.shared.data(for: request)
        if let httpResponse = response as? HTTPURLResponse,
           !(200...299).contains(httpResponse.statusCode) {
            throw URLError(.badServerResponse)
        }

        guard let image = UIImage(data: data) else {
            throw URLError(.cannotDecodeContentData)
        }

        try? data.write(to: fileURL, options: [.atomic])
        return image
    }

    private static func cacheFileURL(for url: URL, in directory: URL) -> URL {
        let digest = SHA256.hash(data: Data(url.absoluteString.utf8))
        let filename = digest.map { String(format: "%02x", $0) }.joined()
        let pathExtension = url.pathExtension.isEmpty ? "image" : url.pathExtension
        return directory
            .appendingPathComponent(filename)
            .appendingPathExtension(pathExtension)
    }
}

@MainActor
final class CachedRemoteImageLoader: ObservableObject {
    @Published private(set) var image: UIImage?

    private let cache: RemoteImageCache
    private var currentURL: URL?
    private var task: Task<Void, Never>?

    init(url: URL?, cache: RemoteImageCache = .shared) {
        self.cache = cache
        currentURL = url

        if let url {
            image = cache.cachedImage(for: url)
        }
    }

    deinit {
        task?.cancel()
    }

    func load(_ url: URL?) {
        if currentURL == url, image != nil || task != nil {
            return
        }

        task?.cancel()
        currentURL = url

        guard let url else {
            image = nil
            task = nil
            return
        }

        if let cachedImage = cache.cachedImage(for: url) {
            image = cachedImage
            task = nil
            return
        }

        image = nil
        task = Task { [weak self] in
            guard let self else {
                return
            }

            do {
                let loadedImage = try await cache.image(for: url)
                guard !Task.isCancelled, currentURL == url else {
                    return
                }
                image = loadedImage
            } catch {
                guard !Task.isCancelled, currentURL == url else {
                    return
                }
            }

            task = nil
        }
    }
}

struct CachedRemoteImage<Content: View, Placeholder: View>: View {
    let url: URL?
    @ViewBuilder let content: (Image) -> Content
    @ViewBuilder let placeholder: () -> Placeholder

    @StateObject private var loader: CachedRemoteImageLoader

    init(
        url: URL?,
        @ViewBuilder content: @escaping (Image) -> Content,
        @ViewBuilder placeholder: @escaping () -> Placeholder
    ) {
        self.url = url
        self.content = content
        self.placeholder = placeholder
        _loader = StateObject(wrappedValue: CachedRemoteImageLoader(url: url))
    }

    var body: some View {
        Group {
            if let image = loader.image {
                content(Image(uiImage: image))
            } else {
                placeholder()
            }
        }
        .onAppear {
            loader.load(url)
        }
        .onChange(of: url) { _, newURL in
            loader.load(newURL)
        }
    }
}

struct RemoteImagePlaceholder: View {
    var body: some View {
        Color(hex: 0xD1D5DB)
    }
}

private extension UIImage {
    var memoryCost: Int {
        let width = Int(size.width * scale)
        let height = Int(size.height * scale)
        return max(width * height * 4, 1)
    }
}
