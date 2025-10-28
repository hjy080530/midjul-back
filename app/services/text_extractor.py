import pdfplumber
import easyocr
import fitz
from typing import Optional
import os


class TextExtractor:
    def __init__(self):
        self.ocr_reader: Optional[easyocr.Reader] = None

    def extract_text_from_pdf(file_path):
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def extract_from_image(self, file_path: str) -> str:
        """이미지 OCR"""
        if self.ocr_reader is None:
            print("OCR 리더 초기화 중...")
            self.ocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)

        try:
            result = self.ocr_reader.readtext(file_path)
            text = ' '.join([item[1] for item in result])
            return text.strip()
        except Exception as e:
            raise Exception(f"이미지 OCR 오류: {str(e)}")

    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # 연속된 공백 제거
        text = ' '.join(text.split())
        # 연속된 줄바꿈 정리
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        return text