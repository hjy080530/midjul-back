from typing import Optional


class Summarizer:
    def __init__(self, model_name: str = "eenzeenee/t5-base-korean-summarization"):
        self.model_name = model_name
        self.summarizer: Optional = None
        print(f"요약기 초기화 (모델은 첫 사용 시 로드)")

    def _load_model(self):
        """첫 호출 시에만 모델 로드"""
        if self.summarizer is None:
            try:
                print(f"요약 모델 로딩 중: {self.model_name}")
                from transformers import pipeline

                self.summarizer = pipeline(
                    "summarization",
                    model=self.model_name,
                    device=-1
                )
                print("요약 모델 로드 완료")
            except Exception as e:
                print(f"요약 모델 로드 실패: {e}")
                print("간단한 추출 요약 사용")

    def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """텍스트 요약"""
        # 텍스트가 너무 짧으면 그대로 반환
        if len(text) < 100:
            return text

        self._load_model()

        if self.summarizer is None:
            return self._extractive_summary(text, num_sentences=2)

        try:
            # 입력 텍스트 길이에 따라 max_length 조정
            text_length = len(text)
            adjusted_max_length = min(max_length, max(text_length // 2, 20))
            adjusted_min_length = min(min_length, adjusted_max_length - 10)

            # 텍스트가 너무 길면 잘라내기
            if text_length > 1024:
                text = text[:1024]

            result = self.summarizer(
                text,
                max_length=adjusted_max_length,
                min_length=adjusted_min_length,
                do_sample=False
            )
            return result[0]['summary_text']
        except Exception as e:
            print(f"요약 생성 오류: {e}")
            return self._extractive_summary(text, num_sentences=2)

    def _extractive_summary(self, text: str, num_sentences: int = 2) -> str:
        """간단한 추출 요약"""
        try:
            import kss

            # kss 6.x는 split 사용
            if hasattr(kss, 'split_sentences'):
                sentences = kss.split_sentences(text)
            else:
                sentences = kss.split(text)

        except Exception as e:
            print(f"KSS 문장 분리 실패: {e}")
            # 폴백: 단순 분할
            sentences = [s.strip() for s in text.split('.') if s.strip()]

        if not sentences or len(sentences) <= num_sentences:
            return text

        return ' '.join(sentences[:num_sentences])