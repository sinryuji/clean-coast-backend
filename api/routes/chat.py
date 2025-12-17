from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import requests
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda

load_dotenv()

router = APIRouter(
    prefix="/v1/chat",
    tags=["chat"]
)

# Alan AI 설정
BASE_URL = os.environ.get("ALAN_API_BASE_URL")
CLIENT_ID = os.environ.get("ALAN_CLIENT_ID")

# 메모리 저장소 (실제로는 Redis나 DB 사용 권장)
chat_memories = {}


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ChatHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]


def alan_question(content: str) -> str:
    """
    사용자가 입력한 'content' 문장을 앨런 API로 보내서
    일반 질문 응답을 받아오는 함수.
    """
    # 실제 API 호출 주소: BASE_URL + 엔드포인트 경로
    url = f"{BASE_URL}/api/v1/question"
    
    # GET 방식에서는 query string 형태로 데이터를 보냄
    params = {"content": content, "client_id": CLIENT_ID}
    
    # requests.get() : 서버에게 "질문"을 보내는 HTTP 요청
    response = requests.get(url, params=params)
    
    print("HTTP 상태 코드:", response.status_code)
    
    # 정상으로 응답된 경우 (200 OK)
    if response.status_code == 200:
        # 응답 본문(JSON 형태)을 파이썬 dict로 변환
        result = response.json()
        # 응답에서 텍스트 추출 (API 응답 구조에 따라 조정 필요)
        return result.get("answer", result.get("response", str(result)))
    else:
        # 오류가 난 경우
        print("오류 발생:", response.text)
        raise Exception(f"Alan AI API 오류 ({response.status_code}): {response.text}")


# LangChain RunnableLambda로 Alan AI 호출을 감싸기
alan_ai_runnable = RunnableLambda(alan_question)

# Chain 구성: 입력 메시지를 받아서 Alan AI로 전달
chat_chain = alan_ai_runnable


def get_or_create_memory(session_id: str) -> List[ChatMessage]:
    """세션별 메모리 가져오기 또는 생성"""
    if session_id not in chat_memories:
        chat_memories[session_id] = []
    return chat_memories[session_id]


@router.post("/message", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    챗봇과 대화하기 (Alan AI 사용)
    
    - **message**: 사용자 메시지
    - **session_id**: 세션 ID (대화 기록 유지용, 기본값: "default")
    """
    try:
        # 세션 메모리 가져오기
        memory = get_or_create_memory(request.session_id)
        
        # 사용자 메시지 저장
        memory.append(ChatMessage(role="user", content=request.message))
        
        # LangChain을 통한 Alan AI API 호출
        response_text = chat_chain.invoke(request.message)
        
        # 어시스턴트 응답 저장
        memory.append(ChatMessage(role="assistant", content=response_text))
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {str(e)}")


@router.get("/history/{session_id}", response_model=ChatHistory)
async def get_history(session_id: str):
    """
    대화 기록 조회
    
    - **session_id**: 세션 ID
    """
    if session_id not in chat_memories:
        return ChatHistory(session_id=session_id, messages=[])
    
    messages = chat_memories[session_id]
    
    return ChatHistory(session_id=session_id, messages=messages)


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    대화 기록 삭제
    
    - **session_id**: 세션 ID
    """
    if session_id in chat_memories:
        del chat_memories[session_id]
        return {"message": f"세션 {session_id}의 대화 기록이 삭제되었습니다"}
    
    return {"message": "해당 세션이 존재하지 않습니다"}


@router.get("/sessions")
async def list_sessions():
    """활성 세션 목록 조회"""
    return {
        "sessions": list(chat_memories.keys()),
        "count": len(chat_memories)
    }
