from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict
import re
from collections import Counter
import httpx
import xml.etree.ElementTree as ET


class KeywordExtractor:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        print(f"키워드 추출 모델 로딩 중: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.kw_model = KeyBERT(self.model)

        # Kiwi 형태소 분석기
        try:
            from kiwipiepy import Kiwi
            self.kiwi = Kiwi()
            print("✅ Kiwi 형태소 분석기 로드 완료")
        except Exception as e:
            print(f"❌ Kiwi 로드 실패: {e}")
            self.kiwi = None

        print("✅ 키워드 추출 모델 로드 완료")

    def _stopwords(self) -> set:
        """불용어 목록"""
        return {
            '것', '이', '그', '저', '이것', '그것', '저것', '수', '데', '바',
            '지', '등', '때', '곳', '점', '년', '월', '일', '시', '분', '초',
            '개', '명', '권', '장', '때문', '경우', '정도', '사람', '사람들',
            '우리', '저희', '이런', '그런', '저런', '어떤', '모든', '각', '몇',
            '하기', '되기', '있기', '없기', '같기', '안', '못', '더', '덜',
            '좀', '약간', '조금', '많이', '예를', '예시', '예', '들어',
            '통해', '위해', '대해', '관해'
        }

    def extract(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """Kiwi + KeyBERT로 키워드 추출"""

        print(f"📝 텍스트 길이: {len(text)}자")

        if not self.kiwi:
            print("⚠️ Kiwi 없음")
            return self._fallback_keywords(text, top_n)

        # 1. Kiwi로 명사만 추출
        nouns = self._extract_nouns_only(text)
        print(f"✅ 명사 추출: {len(set(nouns))}개")

        if len(nouns) == 0:
            return []

        # 2. 빈도 계산
        noun_freq = Counter(nouns)

        # 3. 의미있는 명사만 필터링
        meaningful_nouns = []
        for noun, freq in noun_freq.items():
            if (len(noun) >= 3) or (len(noun) >= 2 and freq >= 2):
                if noun not in self._stopwords():
                    meaningful_nouns.append(noun)

        print(f"✅ 의미있는 명사: {len(meaningful_nouns)}개")

        if len(meaningful_nouns) == 0:
            return []

        # 4. KeyBERT로 중요도 계산
        try:
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words=list(self._stopwords()),
                top_n=min(top_n * 2, len(meaningful_nouns)),
                candidates=meaningful_nouns,
                use_maxsum=True,
                diversity=0.7
            )
            print(f"✅ KeyBERT 추출: {len(keywords)}개")
        except Exception as e:
            print(f"⚠️ KeyBERT 실패: {e}")
            total = sum(noun_freq.values())
            keywords = [
                (noun, freq / total)
                for noun, freq in noun_freq.most_common(top_n)
                if noun in meaningful_nouns
            ]

        final = keywords[:top_n]
        print(f"✅ 최종 키워드: {len(final)}개")
        for word, score in final[:5]:
            print(f"  - {word}: {score:.3f}")

        return final

    def _extract_nouns_only(self, text: str) -> List[str]:
        """Kiwi로 명사만 추출"""
        try:
            result = self.kiwi.analyze(text)
            nouns = []

            for token in result[0][0]:
                if token.tag in ['NNG', 'NNP']:
                    word = token.form
                    if (len(word) >= 2 and
                            word not in self._stopwords() and
                            re.match(r'^[가-힣]+$', word)):
                        nouns.append(word)

            return nouns
        except Exception as e:
            print(f"❌ Kiwi 분석 실패: {e}")
            return []

    def _fallback_keywords(self, text: str, top_n: int) -> List[Tuple[str, float]]:
        """폴백: 정규식 기반"""
        words = re.findall(r'[가-힣]{2,}', text)
        words = [w for w in words if w not in self._stopwords()]

        freq = Counter(words)
        total = sum(freq.values()) if freq else 1

        return [(word, count / total) for word, count in freq.most_common(top_n)]

    async def get_definitions(self, keywords: List[str], api_key: str) -> Dict[str, str]:
        """국립국어원 API로 뜻 가져오기 (XML 응답)"""
        definitions = {}

        print(f"\n📚 국립국어원 사전 조회 시작: {len(keywords)}개")

        for word in keywords:
            if not re.match(r'^[가-힣]+$', word) or len(word) < 2:
                continue

            definition = await self._fetch_definition_from_api(word, api_key)

            if definition:
                definitions[word] = definition
                print(f"  ✅ {word}: {definition[:40]}...")
            else:
                definitions[word] = f"'{word}'에 대한 설명"
                print(f"  ⚠️ {word}: 사전에 없음")

        print(f"📚 사전 조회 완료: {len(definitions)}개\n")

        return definitions

    async def _fetch_definition_from_api(self, word: str, api_key: str) -> str:
        """국립국어원 API 호출"""
        try:
            url = "https://stdict.korean.go.kr/api/search.do"

            params = {
                "key": api_key,
                "type_search": "search",
                "q": word,
                "req_type": "xml",
                "start": "1",
                "num": "10",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    return None

                # 응답 내용 확인
                content = response.content.decode('utf-8')

                # XML 파싱
                try:
                    root = ET.fromstring(response.content)
                except Exception as e:
                    print(f"    ❌ XML 파싱 실패: {e}")
                    return None

                # error 태그가 루트인 경우
                if root.tag == 'error':
                    error_message = root.text
                    print(f"    ❌ API 에러: {error_message}")
                    print(f"    📄 전체 응답:\n{content}\n")
                    return None

                # channel이 아닌 경우
                if root.tag != 'channel':
                    print(f"    ❌ 알 수 없는 루트: {root.tag}")
                    print(f"    📄 전체 응답:\n{content}\n")
                    return None

                # total 확인
                total_elem = root.find('.//total')
                if total_elem is not None:
                    total = total_elem.text
                    if total == '0':
                        return None

                # 첫 번째 item
                item = root.find('.//item')
                if item is None:
                    return None

                # sense > definition
                sense = item.find('.//sense')
                if sense is None:
                    return None

                definition_elem = sense.find('.//definition')
                if definition_elem is None or not definition_elem.text:
                    return None

                definition = definition_elem.text.strip()

                # 80자 제한
                if len(definition) > 80:
                    definition = definition[:80] + "..."

                return definition

        except Exception as e:
            print(f"    ❌ 예외: {e}")
            return None

    def categorize_importance(self, score: float) -> str:
        """중요도 분류"""
        if score >= 0.4:
            return "high"
        elif score >= 0.2:
            return "medium"
        return "low"

    def highlight_text_with_definitions(self, text: str, keywords: List) -> dict:
        """텍스트 하이라이팅 - 조사 포함"""
        import html as html_module

        original_text = text
        sorted_keywords = sorted(keywords, key=lambda x: len(x.word), reverse=True)

        highlights = []

        print(f"🎨 하이라이팅 시작: {len(keywords)}개 키워드")

        for kw in sorted_keywords:
            word = kw.word

            if word not in original_text:
                continue

            # 단어 뒤에 조사/문장부호가 와도 매칭
            # 앞: 한글이 아닌 것, 뒤: 한글 또는 조사 시작 글자
            pattern = re.compile(
                f'(?<![가-힣])({re.escape(word)})(?=[^가-힣]|[은는이가을를에게의도만부터까지]|$)'
            )

            matches = list(pattern.finditer(original_text))

            if len(matches) > 0:
                print(f"  ✅ '{word}': {len(matches)}개 매칭")

            for match in matches:
                start, end = match.span(1)  # 그룹 1만 (단어만)

                # 겹침 확인
                overlap = False
                for h_start, h_end, _, _, _, _ in highlights:
                    if (start < h_end and end > h_start):
                        overlap = True
                        break

                if not overlap:
                    highlights.append((
                        start, end, word,
                        kw.definition or f"'{word}'",
                        kw.importance,
                        kw.score
                    ))

        highlights.sort(key=lambda x: x[0])

        print(f"\n✅ 총 {len(highlights)}개 하이라이트\n")

        # HTML 생성
        html_parts = []
        last_end = 0

        colors = {
            "high": "#FFD700",
            "medium": "#87CEEB",
            "low": "#E8E8E8"
        }

        for start, end, word, definition, importance, score in highlights:
            html_parts.append(original_text[last_end:start])

            word_escaped = html_module.escape(word, quote=True)
            definition_escaped = html_module.escape(definition, quote=True)
            color = colors[importance]

            html_parts.append(
                f'<mark class="highlight-{importance} keyword-tooltip" '
                f'style="background-color:{color}; padding:2px 4px; border-radius:3px; cursor:help;" '
                f'data-word="{word_escaped}" '
                f'data-definition="{definition_escaped}" '
                f'data-score="{score:.2f}">'
                f'{original_text[start:end]}'
                f'</mark>'
            )

            last_end = end

        html_parts.append(original_text[last_end:])

        return {
            "html": ''.join(html_parts),
            "markdown": original_text
        }