from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends

from app.models.schema import ProcessResponse, KeywordItem, DifficultyWord
from app.services.supabase_client import get_supabase
from app.services.text_extractor import TextExtractor
from app.services.keyword_extractor import KeywordExtractor
from app.services.summarizer import Summarizer
from app.services.difficulty_analyzer import DifficultyAnalyzer
from app.core.dependencies import get_current_user_id
from app.config import get_settings
from supabase import Client
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


@router.post("/text", response_model=ProcessResponse)
async def process_text(
        text: str = Form(...),
        user_id: str = Depends(get_current_user_id)
):
    """텍스트 처리 + DB 저장"""
    print(f"\n{'=' * 50}")
    print(f"📥 텍스트 받음: {len(text)}자")
    print(f"👤 사용자: {user_id}")
    print(f"{'=' * 50}\n")

    start_time = time.time()

    # 1. 텍스트 정제
    cleaned_text = text_extractor.clean_text(text)

    # 2. 키워드 추출
    keywords_raw = keyword_extractor.extract(cleaned_text)

    # 3. 국립국어원 뜻풀이
    keyword_words = [word for word, score in keywords_raw]
    definitions = await keyword_extractor.get_definitions(
        keyword_words,
        settings.KOREAN_DICT_API_KEY
    )

    # ✅ 전체 점수 리스트 추출
    all_scores = [score for word, score in keywords_raw]

    keywords = [
        KeywordItem(
            word=word,
            score=score,
            importance=keyword_extractor.categorize_importance(score, all_scores),  # ✅ all_scores 추가
            definition=definitions.get(word)
        )
        for word, score in keywords_raw
    ]

    # 4. 하이라이팅
    highlighted = keyword_extractor.highlight_text_with_definitions(
        cleaned_text, keywords
    )

    # 5. 요약
    summary = summarizer.summarize(cleaned_text)

    # 6. 난이도 분석
    difficult_words_raw = difficulty_analyzer.analyze_difficulty(cleaned_text)
    difficult_words = [DifficultyWord(**word) for word in difficult_words_raw]

    processing_time = time.time() - start_time

    # 7. DB 저장
    document_id = None
    created_at = datetime.now().isoformat()

    try:
        supabase = get_supabase()

        if supabase:
            document_data = {
                "user_id": user_id,
                "title": cleaned_text[:100] + ("..." if len(cleaned_text) > 100 else ""),
                "original_text": cleaned_text,
                "highlighted_html": highlighted['html'],
                "highlighted_markdown": highlighted['markdown'],
                "keywords": [kw.dict() for kw in keywords],
                "difficult_words": [dw.dict() for dw in difficult_words],
                "summary": summary,
                "processing_time": processing_time
            }

            result = supabase.table("documents").insert(document_data).execute()

            if result.data and len(result.data) > 0:
                saved_doc = result.data[0]
                document_id = saved_doc["id"]
                created_at = saved_doc["created_at"]
                print(f"✅ DB 저장 성공: {document_id}")
            else:
                print(f"⚠️ DB 저장 결과 없음")
    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")
        import traceback
        traceback.print_exc()

    # 8. 응답 (DB 저장 실패해도 결과는 반환)
    if not document_id:
        document_id = str(uuid.uuid4())
        print(f"⚠️ 임시 ID 사용: {document_id}")

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

    print(f"⏱️  처리 시간: {processing_time:.2f}초\n")

    return response


@router.post("/pdf", response_model=ProcessResponse)
async def process_pdf(
        file: UploadFile = File(...),
        user_id: str = Depends(get_current_user_id)
):
    """PDF 파일 처리 + DB 저장"""
    print(f"\n{'=' * 50}")
    print(f"📥 PDF 파일 받음: {file.filename}")
    print(f"👤 사용자: {user_id}")
    print(f"{'=' * 50}\n")

    start_time = time.time()

    # 파일 확장자 검증
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    # 임시 파일 저장
    temp_file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"

    try:
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # 1. PDF에서 텍스트 추출
        extracted_text = text_extractor.extract_from_pdf(temp_file_path)

        if not extracted_text or len(extracted_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다")

        # 2. 텍스트 정제
        cleaned_text = text_extractor.clean_text(extracted_text)

        # 3. 키워드 추출
        keywords_raw = keyword_extractor.extract(cleaned_text)

        # 4. 국립국어원 뜻풀이
        keyword_words = [word for word, score in keywords_raw]
        definitions = await keyword_extractor.get_definitions(
            keyword_words,
            settings.KOREAN_DICT_API_KEY
        )

        # ✅ 전체 점수 리스트 추출
        all_scores = [score for word, score in keywords_raw]

        keywords = [
            KeywordItem(
                word=word,
                score=score,
                importance=keyword_extractor.categorize_importance(score, all_scores),  # ✅ all_scores 추가
                definition=definitions.get(word)
            )
            for word, score in keywords_raw
        ]

        # 5. 하이라이팅
        highlighted = keyword_extractor.highlight_text_with_definitions(
            cleaned_text, keywords
        )

        # 6. 요약
        summary = summarizer.summarize(cleaned_text)

        # 7. 난이도 분석
        difficult_words_raw = difficulty_analyzer.analyze_difficulty(cleaned_text)
        difficult_words = [DifficultyWord(**word) for word in difficult_words_raw]

        processing_time = time.time() - start_time

        # 8. DB 저장
        document_id = None
        created_at = datetime.now().isoformat()

        try:
            supabase = get_supabase()

            if supabase:
                document_data = {
                    "user_id": user_id,
                    "title": file.filename,
                    "original_text": cleaned_text,
                    "highlighted_html": highlighted['html'],
                    "highlighted_markdown": highlighted['markdown'],
                    "keywords": [kw.dict() for kw in keywords],
                    "difficult_words": [dw.dict() for dw in difficult_words],
                    "summary": summary,
                    "processing_time": processing_time
                }

                result = supabase.table("documents").insert(document_data).execute()

                if result.data and len(result.data) > 0:
                    saved_doc = result.data[0]
                    document_id = saved_doc["id"]
                    created_at = saved_doc["created_at"]
                    print(f"✅ DB 저장 성공: {document_id}")
                else:
                    print(f"⚠️ DB 저장 결과 없음")
        except Exception as e:
            print(f"❌ DB 저장 실패: {e}")
            import traceback
            traceback.print_exc()

        # 9. 응답 (DB 저장 실패해도 결과는 반환)
        if not document_id:
            document_id = str(uuid.uuid4())
            print(f"⚠️ 임시 ID 사용: {document_id}")

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

        print(f"⏱️  처리 시간: {processing_time:.2f}초\n")

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ PDF 처리 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF 처리 중 오류 발생: {str(e)}")
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"🗑️  임시 파일 삭제: {temp_file_path}")


@router.get("/documents/{document_id}")
async def get_document(
        document_id: str,
        user_id: str = Depends(get_current_user_id)
):
    """문서 상세 조회"""
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="DB 연결 불가")

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
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 문서 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="문서 조회 실패")


@router.get("/documents")
async def get_documents(
        user_id: str = Depends(get_current_user_id),
        limit: int = 20,
        offset: int = 0
):
    """문서 목록 조회"""
    try:
        supabase = get_supabase()
        if not supabase:
            return []

        result = supabase.table("documents") \
            .select("id, title, summary, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return result.data
    except Exception as e:
        print(f"❌ 문서 목록 조회 실패: {e}")
        return []


@router.delete("/documents/{document_id}")
async def delete_document(
        document_id: str,
        user_id: str = Depends(get_current_user_id)
):
    """문서 삭제"""
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="DB 연결 불가")

        result = supabase.table("documents") \
            .delete() \
            .eq("id", document_id) \
            .eq("user_id", user_id) \
            .execute()

        return {"message": "문서가 삭제되었습니다"}
    except Exception as e:
        print(f"❌ 문서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="문서 삭제 실패")