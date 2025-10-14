from fastapi import APIRouter, File, UploadFile, Form, HTTPException

from app.models.schema import ProcessResponse, DifficultyWord, KeywordItem
from app.services.text_extractor import TextExtractor
from app.services.keyword_extractor import KeywordExtractor
from app.services.summarizer import Summarizer
from app.services.difficulty_analyzer import DifficultyAnalyzer
from app.config import get_settings
import time
import os
import aiofiles
import uuid
from datetime import datetime

router = APIRouter(prefix="/process", tags=["processing"])
settings = get_settings()

# 서비스 인스턴스
text_extractor = TextExtractor()
keyword_extractor = KeywordExtractor(settings.KEYWORD_MODEL)
summarizer = Summarizer(settings.SUMMARY_MODEL)
difficulty_analyzer = DifficultyAnalyzer()

# 임시 메모리 저장소
documents_store = {}

from app.config import get_settings

settings = get_settings()


@router.post("/text", response_model=ProcessResponse)
async def process_text(text: str = Form(...)):
    """텍스트 처리 - 인증 없음"""
    print(f"\n{'=' * 50}")
    print(f"📥 텍스트 받음: {len(text)}자")
    print(f"{'=' * 50}\n")

    start_time = time.time()

    cleaned_text = text_extractor.clean_text(text)

    # 키워드 추출
    keywords_raw = keyword_extractor.extract(cleaned_text)

    # 키워드 뜻풀이 조회 (국립국어원 API)
    keyword_words = [word for word, score in keywords_raw]
    definitions = await keyword_extractor.get_definitions(
        keyword_words,
        settings.KOREAN_DICT_API_KEY
    )

    keywords = [
        KeywordItem(
            word=word,
            score=score,
            importance=keyword_extractor.categorize_importance(score),
            definition=definitions.get(word)
        )
        for word, score in keywords_raw
    ]

    # 하이라이팅
    highlighted = keyword_extractor.highlight_text_with_definitions(
        cleaned_text, keywords
    )

    # 요약
    summary = summarizer.summarize(cleaned_text)

    # 난이도 분석
    difficult_words_raw = difficulty_analyzer.analyze_difficulty(cleaned_text)
    difficult_words = [DifficultyWord(**word) for word in difficult_words_raw]

    processing_time = time.time() - start_time

    document_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    response = ProcessResponse(
        id=document_id,
        original_text=cleaned_text,
        highlighted_html=highlighted['html'],
        highlighted_markdown=highlighted['markdown'],
        keywords=keywords,
        difficult_words=difficult_words,
        summary=summary,
        processing_time=processing_time,
        created_at=created_at
    )

    documents_store[document_id] = {
        "id": document_id,
        "original_text": cleaned_text,
        "highlighted_html": highlighted['html'],
        "highlighted_markdown": highlighted['markdown'],
        "keywords": [kw.dict() for kw in keywords],
        "difficult_words": [dw.dict() for dw in difficult_words],
        "summary": summary,
        "processing_time": processing_time,
        "created_at": created_at
    }

    print(f"✅ 문서 저장됨: {document_id}")
    print(f"⏱️  처리 시간: {processing_time:.2f}초\n")

    return response

@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """문서 조회 - 인증 없음"""
    print(f"📖 문서 조회: {document_id}")

    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    doc = documents_store[document_id]

    return ProcessResponse(
        id=doc["id"],
        original_text=doc["original_text"],
        highlighted_html=doc["highlighted_html"],
        highlighted_markdown=doc["highlighted_markdown"],
        keywords=[KeywordItem(**kw) for kw in doc["keywords"]],
        difficult_words=[DifficultyWord(**dw) for dw in doc["difficult_words"]],
        summary=doc["summary"],
        processing_time=doc["processing_time"],
        created_at=doc["created_at"]
    )


@router.get("/documents")
async def get_documents():
    """문서 목록 - 인증 없음"""
    return [
        {
            "id": doc["id"],
            "title": doc["original_text"][:50] + "...",
            "summary": doc["summary"],
            "created_at": doc["created_at"]
        }
        for doc in documents_store.values()
    ]


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """문서 삭제 - 인증 없음"""
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    del documents_store[document_id]
    print(f"🗑️ 문서 삭제됨: {document_id}")

    return {"message": "문서가 삭제되었습니다"}


@router.post("/pdf", response_model=ProcessResponse)
async def process_pdf(file: UploadFile = File(...)):
    """PDF 파일 처리 - 인증 없음"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    file_path = f"{settings.UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    try:
        print(f"📄 PDF 처리 중: {file.filename}")

        text = text_extractor.extract_from_pdf(file_path)

        start_time = time.time()
        cleaned_text = text_extractor.clean_text(text)
        keywords_raw = keyword_extractor.extract(cleaned_text)
        keywords = [
            KeywordItem(word=word, score=score, importance=keyword_extractor.categorize_importance(score))
            for word, score in keywords_raw
        ]
        highlighted = keyword_extractor.highlight_text(cleaned_text, keywords_raw)
        summary = summarizer.summarize(cleaned_text)
        difficult_words_raw = difficulty_analyzer.analyze_difficulty(cleaned_text)
        difficult_words = [DifficultyWord(**word) for word in difficult_words_raw]
        processing_time = time.time() - start_time

        document_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        response = ProcessResponse(
            id=document_id,
            original_text=cleaned_text,
            highlighted_html=highlighted['html'],
            highlighted_markdown=highlighted['markdown'],
            keywords=keywords,
            difficult_words=difficult_words,
            summary=summary,
            processing_time=processing_time,
            created_at=created_at
        )

        documents_store[document_id] = {
            "id": document_id,
            "original_text": cleaned_text,
            "highlighted_html": highlighted['html'],
            "highlighted_markdown": highlighted['markdown'],
            "keywords": [kw.dict() for kw in keywords],
            "difficult_words": [dw.dict() for dw in difficult_words],
            "summary": summary,
            "processing_time": processing_time,
            "created_at": created_at
        }

        print(f"✅ PDF 문서 저장됨: {document_id}")

        return response

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ 임시 파일 삭제: {file.filename}")