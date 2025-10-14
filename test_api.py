import httpx
import xml.etree.ElementTree as ET

API_KEY = "FB926305D20DFB92DBEE11E8DF7BB3C7"


def test_api(word: str):
    url = "https://stdict.korean.go.kr/api/search.do"

    params = {
        "key": API_KEY,
        "type_search": "search",
        "q": word,
        "req_type": "xml",
        "start": "1",
        "num": "10",
    }

    print(f"\n{'=' * 50}")
    print(f"🔍 검색어: {word}")
    print(f"📡 요청 URL: {url}")
    print(f"📋 파라미터: {params}")
    print(f"{'=' * 50}\n")

    try:
        response = httpx.get(url, params=params, timeout=10.0)

        print(f"📡 응답 상태: {response.status_code}")
        print(f"📄 응답 길이: {len(response.content)}자")

        content = response.content.decode('utf-8')
        print(f"\n📄 응답 내용:\n{content}\n")

        if response.status_code != 200:
            return

        # XML 파싱
        root = ET.fromstring(response.content)

        # error 확인
        error = root.find('.//error')
        if error is not None:
            print(f"❌ API 에러: {error.text}")
            return

        # channel > total
        channel = root.find('.//channel')
        if channel:
            total = channel.find('.//total')
            if total is not None:
                print(f"📊 검색 결과: {total.text}건")

        # item 찾기
        items = channel.findall('.//item') if channel else []

        if not items:
            print("⚠️ 검색 결과 없음")
            return

        for i, item in enumerate(items[:3], 1):
            print(f"\n--- 결과 {i} ---")

            word_elem = item.find('.//word')
            if word_elem is not None:
                print(f"표제어: {word_elem.text}")

            sense = item.find('.//sense')
            if sense:
                definition = sense.find('.//definition')
                if definition is not None and definition.text:
                    print(f"뜻: {definition.text}")

    except Exception as e:
        print(f"❌ 예외: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 테스트할 단어들
    test_words = ["극단", "공존", "개념", "의미", "행복"]

    for word in test_words:
        test_api(word)
        print("\n" + "=" * 80 + "\n")