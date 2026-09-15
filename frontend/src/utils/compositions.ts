import type { DeckCompositionSummary } from '../types/composition'

export const compositionPreviewCards = (composition: DeckCompositionSummary) => {
  return [...(composition.cards || [])]
    .sort((a, b) => b.count - a.count || (a.name || a.slug).localeCompare(b.name || b.slug))
    .slice(0, 4)
}

export const compositionLabel = (composition: DeckCompositionSummary): string => {
  return compositionPreviewCards(composition)
    .slice(0, 2)
    .map(card => card.name || card.slug)
    .join(' / ') || 'Empty composition'
}
