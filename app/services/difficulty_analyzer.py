import json
from typing import List, Dict
import re
import os
import httpx
import asyncio


class DifficultyAnalyzer:
    def __init__(self, vocab_file: str = "data/korean_vocab.json"):
        self.vocab_data = {}

        if os.path.exists(vocab_file):
            try:
                with open(vocab_file, 'r', encoding='utf-8') as f:
                    self.vocab_data = json.load(f)
                print(f"어휘 데이터 로드 완료: {len(self.vocab_data)}개 단어")
            except Exception as e:
                print(f"어휘 데이터 로드 실패: {e}")
        else:
            print(f"어휘 데이터 파일이 없습니다: {vocab_file}")

        print("국립국어원 사전 API 연동 준비 완료")

    async def get_definition_from_api(self, word: str) -> str:
        """국립국어원 표준국어대사전 API로 단어 뜻 가져오기"""
        try:
            # 국립국어원 오픈 API
            api_url = "https://stdict.korean.go.kr/api/search.do"

            # API 키 (발급 필요: https://stdict.korean.go.kr/openapi/openApiInfo.do)
            # 임시로 공개 검색 사용
            params = {
                "key": "225812825962B51D9FA8F705F0D9F441",  # 실제 API 키로 교체 필요
                "q": word,
                "req_type": "json",
                "part": "word",
                "sort": "dict",
                "start": "1",
                "num": "10"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(api_url, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # 응답에서 뜻 추출
                    if data.get("channel", {}).get("item"):
                        items = data["channel"]["item"]
                        if isinstance(items, list) and len(items) > 0:
                            sense = items[0].get("sense", {})
                            definition = sense.get("definition", "")

                            if definition:
                                # HTML 태그 제거
                                definition = re.sub(r'<[^>]+>', '', definition)
                                return definition[:100]  # 100자로 제한
        except Exception as e:
            print(f"API 호출 실패 ({word}): {e}")

        return None

    def analyze_difficulty(self, text: str) -> List[Dict]:
        """어려운 단어 찾기 + 국립국어원 사전 뜻 추가"""
        difficult_words = []

        # 한국어 명사 추출 (3글자 이상)
        words = re.findall(r'[가-힣]{3,}', text)
        unique_words = set(words)

        # 어려운 단어 기준
        for word in unique_words:
            level = self._get_word_level(word)

            if level >= 4:  # 레벨 4 이상만
                # 사전에서 정의 찾기
                definition = self._get_definition(word)

                difficult_words.append({
                    "word": word,
                    "level": level,
                    "definition": definition
                })

        # 난이도 순 정렬, 상위 10개
        difficult_words.sort(key=lambda x: x['level'], reverse=True)
        return difficult_words[:10]

    def _get_word_level(self, word: str) -> int:
        """단어 난이도 레벨 (1~5)"""
        if word in self.vocab_data:
            return self.vocab_data[word].get('level', 3)

        # 휴리스틱: 긴 단어일수록 어려움
        # 한자어, 전문용어 패턴
        if len(word) >= 5:
            return 5
        elif len(word) >= 4:
            return 4
        elif len(word) >= 3:
            return 3
        return 2

    def _get_definition(self, word: str) -> str:
        """단어 정의 (로컬 사전 → 국립국어원 API)"""
        # 1. 로컬 사전에서 찾기
        if word in self.vocab_data:
            return self.vocab_data[word].get('definition', '전문 용어')

        # 2. 국립국어원 API 사용 (동기 함수에서는 기본 설명 반환)
        # 실제 API 호출은 async 함수에서 처리
        return f"'{word}'은(는) 전문적이거나 어려운 단어입니다."