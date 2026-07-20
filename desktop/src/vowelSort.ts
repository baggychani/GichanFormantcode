/** IPA-aware vowel label ordering for analysis tables and layer lists. */

export const IPA_VOWEL_SEQUENCE = [
  "a", "ɑ", "æ", "ɐ", "ɑ̃", "e", "ə", "ɚ", "ɵ", "ɘ", "ɛ", "ɜ", "ɝ", "ɛ̃", "ɞ",
  "i", "ɪ", "ɨ", "ɪ̈", "o", "ɔ", "œ", "ɒ", "ɔ̃", "ɶ", "ø", "u", "ʊ", "ʉ", "ʌ",
  "w", "ɯ", "ʍ", "ɰ", "y", "ɣ", "ʎ", "ʏ", "ɤ",
];

export function sortVowels(vowels: string[]) {
  const rank = new Map(IPA_VOWEL_SEQUENCE.map((vowel, index) => [vowel, index]));
  const bases = [...IPA_VOWEL_SEQUENCE].sort((a, b) => b.length - a.length);
  return [...vowels].sort((left, right) => {
    const leftBase = bases.find((base) => left.startsWith(base));
    const rightBase = bases.find((base) => right.startsWith(base));
    if (leftBase && rightBase) {
      return (rank.get(leftBase) ?? 0) - (rank.get(rightBase) ?? 0)
        || left.slice(leftBase.length).localeCompare(right.slice(rightBase.length));
    }
    if (leftBase) return -1;
    if (rightBase) return 1;
    return left.localeCompare(right);
  });
}
