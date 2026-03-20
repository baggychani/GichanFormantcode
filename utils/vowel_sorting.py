# utils/vowel_sorting.py
"""
IPA 모음 심볼의 언어학적 순서를 정의하고 정렬 키를 제공하는 유틸리티입니다.
기본 알파벳 순서 대신 사용자가 지정한 IPA 그룹 순서에 따라 정렬합니다.
"""

# 사용자 정의 IPA 순서 (그룹별)
# a | ɑ, æ, ɐ, ɑ̃
# e | ə, ɚ, ɵ, ɘ
# ɜ | ɛ, ɜ, ɝ, ɛ̃, ɞ
# i | ɪ, ɨ, ɪ̈
# o | ɔ, œ, ɒ, ɔ̃, ɶ
# ø | ø
# u | ʊ, ʉ
# ʌ | ʌ
# w | ɯ, ʍ, ɰ
# y | ɣ, ʎ, ʏ, ɤ
IPA_VOWEL_SEQUENCE = [
    # a 그룹
    'a', 'ɑ', 'æ', 'ɐ', 'ɑ̃',
    # e 그룹
    'e', 'ə', 'ɚ', 'ɵ', 'ɘ',
    # ɜ 그룹 (사용자 요청 리스트 순서: ɛ, ɜ, ɝ, ɛ̃, ɞ)
    'ɛ', 'ɜ', 'ɝ', 'ɛ̃', 'ɞ',
    # i 그룹
    'i', 'ɪ', 'ɨ', 'ɪ̈',
    # o 그룹
    'o', 'ɔ', 'œ', 'ɒ', 'ɔ̃', 'ɶ',
    # ø 그룹
    'ø',
    # u 그룹
    'u', 'ʊ', 'ʉ',
    # ʌ 그룹
    'ʌ',
    # w 그룹
    'w', 'ɯ', 'ʍ', 'ɰ',
    # y 그룹
    'y', 'ɣ', 'ʎ', 'ʏ', 'ɤ'
]

# 빠른 조회를 위한 맵 생성
VOWEL_TO_RANK = {v: i for i, v in enumerate(IPA_VOWEL_SEQUENCE)}

def get_vowel_sort_key(vowel):
    """
    모음 정렬을 위한 키를 반환합니다.
    순서: IPA_VOWEL_SEQUENCE에 정의된 순서 -> 그 외(알파벳 순)
    장음 기호(:) 등이 붙은 경우 해당 베이스 모음 그룹 내에서 순서대로 정렬되도록 처리합니다.
    """
    v = str(vowel).strip()
    
    # 1. 정의된 IPA 순서 중 가장 긴 일치 접두사를 찾습니다.
    # (ɑ̃, ɪ̈ 처럼 두 글자인 경우를 먼저 처리하기 위해 길이 역순으로 확인)
    sorted_bases = sorted(IPA_VOWEL_SEQUENCE, key=len, reverse=True)
    for base in sorted_bases:
        if v.startswith(base):
            suffix = v[len(base):]
            return (0, VOWEL_TO_RANK[base], suffix)
    
    # 2. 정의되지 않은 경우 (알파벳 순서로 뒤에 배치)
    return (1, v.lower(), "")

def sort_vowels(vowels):
    """모음 리스트를 사용자 정의 순서에 따라 정렬하여 반환합니다."""
    return sorted(list(vowels), key=get_vowel_sort_key)
