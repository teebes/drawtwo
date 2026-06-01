import SwiftUI

struct HowToView: View {
    @EnvironmentObject private var authStore: AuthStore

    var body: some View {
        ArchetypeScreen {
            ScrollView {
                VStack(spacing: 0) {
                    topBar
                        .padding(.horizontal, 18)
                        .padding(.top, 6)
                        .padding(.bottom, 16)

                    VStack(spacing: 24) {
                        Text("How to Play")
                            .font(.archetypeBody(28, weight: .bold))
                            .foregroundStyle(ArchetypeTheme.text)
                            .frame(maxWidth: .infinity)

                        HowToGuideContent()
                    }
                    .frame(maxWidth: 672)
                    .padding(.horizontal, 18)
                    .padding(.top, 20)
                    .padding(.bottom, 32)
                }
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(true)
        .onAppear {
            CaptureStateRecorder.record("how-to")
        }
    }

    private var topBar: some View {
        DrawTwoTopBar {
            ArchetypeProfileLink(user: authStore.user) {
                ProfileView()
            }
        }
    }
}

struct HowToGuideContent: View {
    var horizontalInset: CGFloat = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 32) {
            GuideText("A game opposes two heroes, and ends when a hero's health reaches 0 or when all cards in the deck are drawn.")

            HeroBoardGuide()

            GuideText("Players start with 3 cards and 0 energy. Each turn, all players gain 1 energy, up to 10.")
            GuideText("Cards have energy cost, and to play it, the player must have enough energy to pay for it.")

            SampleCardsGuide()

            GuideText("A trait is a special ability that a card can have. Possible traits are:")

            VStack(alignment: .leading, spacing: 14) {
                TraitGuideRow(glyph: "📣", text: "On Play - effect is executed when the card is played.")
                TraitGuideRow(glyph: "💀", text: "On Death - effect is executed when the creature dies.")
                TraitGuideRow(glyph: "👁️", text: "Stealth - creature cannot be directly targeted until it attacks.")
                TraitGuideRow(glyph: "🛡️", text: "Taunt - creature must be attacked before other targets.")
                TraitGuideRow(glyph: "🏹", text: "Ranged - creature can attack without taking counterattack damage.")
                TraitGuideRow(glyph: "⚔️", text: "Charge - creature can attack immediately when played.")
                TraitGuideRow(glyph: "⭐", text: "Unique - only one copy of this card can exist in your deck.")
            }

            Text("Misc Rules")
                .font(.archetypeBody(22, weight: .semibold))
                .foregroundStyle(ArchetypeTheme.text)
                .frame(maxWidth: .infinity)
                .padding(.top, 8)

            GuideText("If a deck runs out of cards and a card needs to be drawn, the player out of cards loses the game.")
            GuideText("When creatures are first played, they are in exhausted state. The exhausted state is removed at the end of each turn. A creature that is exhausted cannot attack.")
            GuideText("Taunt only blocks physical damage. Spell damage will bypass it.")
            GuideText("Using the Remove spell will bypass the On Death trait on the removed card.")
            GuideText("When a player goes second, they start with an extra Power-Up card in their hand, which if used gives them 1 extra energy for the remainder of the turn.")
        }
        .frame(maxWidth: 672)
        .padding(.horizontal, horizontalInset)
    }
}

private struct GuideText: View {
    private static let fontSize: CGFloat = 16

    let text: String
    var centered = false

    init(_ text: String, centered: Bool = false) {
        self.text = text
        self.centered = centered
    }

    var body: some View {
        Text(text)
            .font(.archetypeBody(Self.fontSize))
            .foregroundStyle(Color(hex: 0xD1D5DB))
            .multilineTextAlignment(centered ? .center : .leading)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: centered ? .center : .leading)
    }
}

private struct TraitGuideRow: View {
    let glyph: String
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Text(glyph)
                .font(.system(size: 16, weight: .semibold))
                .frame(width: 32, height: 32)
                .background(Color.white)
                .clipShape(Circle())
                .overlay(Circle().stroke(Color(hex: 0x111827), lineWidth: 1))
                .shadow(color: Color.black.opacity(0.24), radius: 4, x: 0, y: 2)
                .offset(y: -3)

            Text(text)
                .font(.archetypeBody(16))
                .foregroundStyle(Color(hex: 0xD1D5DB))
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 0)
        }
    }
}

private struct HeroBoardGuide: View {
    private let opponentURL = AppConfig.heroArtURL(slug: "healer").flatMap(URL.init(string:))
    private let playerURL = AppConfig.heroArtURL(slug: "berserker").flatMap(URL.init(string:))

    var body: some View {
        VStack(spacing: 0) {
            GuideHeroRow(
                title: "Opponent Hero",
                health: "20",
                imageURL: opponentURL,
                active: false
            )

            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)

            VStack(alignment: .leading, spacing: 28) {
                GuideText("The first player whose hero's health reaches 0 loses the game.")

                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .center, spacing: 8) {
                        Text("The")
                            .font(.archetypeBody(16))
                            .foregroundStyle(Color(hex: 0xD1D5DB))

                        RoundedRectangle(cornerRadius: 2)
                            .stroke(ArchetypeTheme.gold2, lineWidth: 4)
                            .frame(width: 24, height: 24)

                        Text("border around the hero")
                            .font(.archetypeBody(16))
                            .foregroundStyle(Color(hex: 0xD1D5DB))
                    }

                    GuideText("portrait indicates whose turn it is.")
                }
            }
            .frame(maxWidth: .infinity, minHeight: 300)
            .padding(.horizontal, 18)

            Rectangle()
                .fill(ArchetypeTheme.border)
                .frame(height: 1)

            GuideHeroRow(
                title: "Own Hero",
                health: "20",
                imageURL: playerURL,
                active: true
            )
        }
        .frame(maxWidth: 320)
        .overlay(
            Rectangle()
                .stroke(ArchetypeTheme.border, lineWidth: 1)
        )
        .frame(maxWidth: .infinity)
    }
}

private struct GuideHeroRow: View {
    let title: String
    let health: String
    let imageURL: URL?
    let active: Bool

    var body: some View {
        HStack(spacing: 0) {
            ZStack {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    default:
                        LinearGradient(
                            colors: [ArchetypeTheme.panel2, ArchetypeTheme.gold.opacity(0.28)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    }
                }
                .frame(width: 96, height: 96)
                .clipped()

                Color.black.opacity(0.42)

                Text(health)
                    .font(.archetypeBody(22, weight: .black))
                    .foregroundStyle(Color.white)
            }
            .frame(width: 96, height: 96)
            .overlay(
                Rectangle()
                    .inset(by: active ? 2 : 0.5)
                    .stroke(active ? ArchetypeTheme.gold2 : ArchetypeTheme.border, lineWidth: active ? 4 : 1)
            )

            HStack(spacing: 9) {
                Text("←")
                    .font(.archetypeBody(22, weight: .semibold))
                    .foregroundStyle(Color(hex: 0xD1D5DB))

                Text(title)
                    .font(.archetypeBody(16, weight: .semibold))
                    .foregroundStyle(Color(hex: 0xD1D5DB))
            }
            .frame(maxWidth: .infinity)
        }
        .frame(height: 96)
    }
}

private struct SampleCardsGuide: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack {
                Spacer()
                GuideCard(
                    name: "Brute",
                    cost: 3,
                    attack: 4,
                    health: 5,
                    artURL: AppConfig.cardArtURL(slug: "brute").flatMap(URL.init(string:)),
                    detail: "Creatures stay on the board with attack and health.",
                    traitGlyph: nil,
                    showsDetails: false
                )
                .frame(maxWidth: 190)
                Spacer()
            }

            GuideText("The card above is a creature, which means that once played it will become a creature on the board, with attack and health. The three values mean:")

            VStack(alignment: .leading, spacing: 10) {
                GuideStatLine(color: ArchetypeTheme.gold2, text: "3 - Energy cost to play this card.")
                GuideStatLine(color: ArchetypeTheme.red, text: "4 - Attack damage dealt when attacking with this creature.")
                GuideStatLine(color: ArchetypeTheme.green, text: "5 - Health of the creature, when this reaches 0 the creature is destroyed.")
            }
            .frame(maxWidth: 280)
            .frame(maxWidth: .infinity)

            GuideText("Creatures deal physical damage, and whenever they receive physical damage they counterattack with their own attack damage.")
            GuideText("Spell cards, on the other hand, have neither attack nor health, and their effects are immediately executed and set to the discard pile.")

            HStack {
                Spacer()
                GuideCard(
                    name: "Zap",
                    cost: 1,
                    attack: nil,
                    health: nil,
                    artURL: AppConfig.cardArtURL(slug: "zap").flatMap(URL.init(string:)),
                    detail: "Deal 2 damage to an enemy.",
                    traitGlyph: "📣",
                    showsDetails: true
                )
                .frame(maxWidth: 190)
                Spacer()
            }

            GuideText("Unlike physical damage, spell damage does not trigger counter attacks, and it is not affected by the Taunt trait.")
            GuideText("The upper-left hand corner of the card shows one of the card's traits, in this case On Play.")
        }
    }
}

private struct GuideCard: View {
    let name: String
    let cost: Int
    let attack: Int?
    let health: Int?
    let artURL: URL?
    let detail: String
    let traitGlyph: String?
    let showsDetails: Bool

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hex: 0xD1D5DB))

            cardArt
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: 12))

            if showsDetails {
                VStack(spacing: 0) {
                    Text(name)
                        .font(.archetypeDisplay(16, weight: .bold))
                        .foregroundStyle(Color.white)
                        .lineLimit(1)
                        .minimumScaleFactor(0.72)
                        .frame(maxWidth: .infinity)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 8)
                        .background(Color.black.opacity(0.78))

                    Spacer(minLength: 0)

                    Text(detail)
                        .font(.archetypeBody(10, weight: .medium))
                        .foregroundStyle(Color.white)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.black.opacity(0.78))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .padding(10)
                }
            }
        }
        .aspectRatio(5 / 7, contentMode: .fit)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: 0x111827), lineWidth: 2)
        )
        .overlay(alignment: .topTrailing) {
            GuideStatBadge(text: "\(cost)", color: ArchetypeTheme.sky)
                .offset(x: 10, y: -10)
        }
        .overlay(alignment: .topLeading) {
            if let traitGlyph {
                GuideTraitBadge(text: traitGlyph)
                    .offset(x: -10, y: -10)
            }
        }
        .overlay(alignment: .bottomLeading) {
            if let attack {
                GuideStatBadge(text: "\(attack)", color: ArchetypeTheme.red)
                    .offset(x: -10, y: 10)
            }
        }
        .overlay(alignment: .bottomTrailing) {
            if let health {
                GuideStatBadge(text: "\(health)", color: ArchetypeTheme.green)
                    .offset(x: 10, y: 10)
            }
        }
    }

    @ViewBuilder
    private var cardArt: some View {
        if let artURL {
            AsyncImage(url: artURL) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                default:
                    placeholder
                }
            }
        } else {
            placeholder
        }
    }

    private var placeholder: some View {
        DrawTwoCardBackFill(logoSize: 72, showsWordmark: true)
    }
}

private struct GuideStatBadge: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.archetypeBody(13, weight: .black))
            .foregroundStyle(Color.white)
            .frame(width: 32, height: 32)
            .background(color)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color(hex: 0x111827), lineWidth: 1))
            .shadow(color: Color.black.opacity(0.26), radius: 5, x: 0, y: 2)
    }
}

private struct GuideTraitBadge: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.system(size: 13, weight: .black))
            .frame(width: 32, height: 32)
            .background(Color.white)
            .clipShape(Circle())
            .overlay(Circle().stroke(Color(hex: 0x111827), lineWidth: 1))
            .shadow(color: Color.black.opacity(0.26), radius: 5, x: 0, y: 2)
    }
}

private struct GuideStatLine: View {
    let color: Color
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(color)
                .frame(width: 10, height: 10)
                .padding(.top, 4)

            Text(text)
                .font(.archetypeBody(14))
                .foregroundStyle(Color(hex: 0xD1D5DB))
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct GuideRuleSection: View {
    let title: String
    let rules: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ArchetypeWebSectionTitle(title: title)

            ArchetypeWebPanel(padding: 0) {
                VStack(spacing: 0) {
                    ForEach(Array(rules.enumerated()), id: \.offset) { index, rule in
                        HStack(alignment: .top, spacing: 12) {
                            Text("\(index + 1)")
                                .font(.archetypeBody(12, weight: .black))
                                .foregroundStyle(Color(hex: 0x111827))
                                .frame(width: 24, height: 24)
                                .background(ArchetypeTheme.gold2)
                                .clipShape(Circle())

                            Text(rule)
                                .font(.archetypeBody(14))
                                .foregroundStyle(Color(hex: 0xD1D5DB))
                                .fixedSize(horizontal: false, vertical: true)

                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 13)

                        if index < rules.count - 1 {
                            Divider()
                                .overlay(ArchetypeTheme.border)
                        }
                    }
                }
            }
        }
    }
}
