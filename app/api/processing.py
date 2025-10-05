from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from app.services.supabase_client import get_supabase
from app.services.text_extractor import TextExtractor
from app.services.keyword_extractor import KeywordExtractor
from app.services.summarizer import Summarizer
from app.services.difficulty_analyzer import DifficultyAnalyzer
from app.models.schemas import ProcessResponse, KeywordItem, DifficultyWord, DocumentListItem
from app.core.dependencies import get_current_user_id
from app.config import get_settings
from supabase import Client
import time
import os
import aiofiles
from typing import List

router = APIRouter(prefix="/process", tags=["processing"])
settings = get_settings()

# 서비스 인스턴스
text_extractor = TextExtractor()
keyword_extractor = KeywordExtractor(settings.KEYWORD_MODEL)
summarizer = Summarizer(settings.SUMMARY_MODEL)
difficulty_analyzer = DifficultyAnalyzer()


@router.post("/text", response_model=ProcessResponse)
async def process_text(
        text: str = Form(...),
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase)
):
    """텍스트 처리"""
    start_time = time.time()

    # 1. 텍스트 정제
    cleaned_text = text_extractor.clean_text(text)

    # 2. 키워드 추출
    keywords_raw = keyword_extractor.extract(cleaned_text)
    keywords = [
        KeywordItem(
            word=word,
            score=score,
            importance=keyword_extractor.categorize_importance(score)
        )
        for word, score in keywords_raw
    ]

    # 3. 하이라이팅
    highlighted = keyword_extractor.highlight_text(cleaned_text, keywords_raw)

    # 4. 요약
    summary = summarizer.summarize(cleaned_text)

    # 5. 난이도 분석
    difficult_words_raw = difficulty_analyzer.analyze_difficulty(cleaned_text)
    difficult_words = [DifficultyWord(**word) for word in difficult_words_raw]

    processing_time = time.time() - start_time

    # 6. Supabase에 저장
    document_data = {
        "user_id": user_id,
        "title": cleaned_text[:50] + "...",  # 첫 50자를 제목으로
        "original_text": cleaned_text,
        "highlighted_html": highlighted['html'],
        "highlighted_markdown": highlighted['markdown'],
        "keywords": [kw.dict() for kw in keywords],
        "summary": summary,
        "difficult_words": [dw.dict() for dw in difficult_words],
        "processing_time": processing_time
    }

    result = supabase.table("documents").insert(document_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="문서 저장 실패")

    saved_doc = result.data[0]

    return ProcessResponse(
        id=saved_doc["id"],
        original_text=cleaned_text,
        highlighted_html=highlighted['html'],
        highlighted_markdown=highlighted['markdown'],
        keywords=keywords,
        difficult_words=difficult_words,
        summary=summary,
        processing_time=processing_time,
        created_at=saved_doc["created_at"]
    )


@router.post("/pdf", response_model=ProcessResponse)
async def process_pdf(
        file: UploadFile = File(...),
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase)
):
    """PDF 파일 처리"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능")

    file_path = f"{settings.UPLOAD_DIR}/{user_id}_{file.filename}"

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    try:
        text = text_extractor.extract_from_pdf(file_path)

        # process_text 로직 재사용
        # ... (위와 동일)

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/documents", response_model=List[DocumentListItem])
async def get_user_documents(
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase),
        limit: int = 20,
        offset: int = 0
):
    """사용자 문서 목록 조회"""
    result = supabase.table("documents") \
        .select("id, title, summary, created_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    return result.data


@router.get("/documents/{document_id}", response_model=ProcessResponse)
async def get_document(
        document_id: str,
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase)
):
    """특정 문서 상세 조회"""
    result = supabase.table("documents") \
        .select("*") \
        .eq("id", document_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    doc = result.data

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


@router.delete("/documents/{document_id}")
async def delete_document(
        document_id: str,
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase)
):
    """문서 삭제"""
    result = supabase.table("documents") \
        .delete() \
        .eq("id", document_id) \
        .eq("user_id", user_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    return {"message": "문서가 삭제되었습니다"}