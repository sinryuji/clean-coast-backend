from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import requests
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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
def call_alan_with_formatted_prompt(prompt_value):
    """프롬프트 값을 받아서 Alan AI에 전달"""
    # ChatPromptValue 객체를 문자열로 변환
    # messages 속성에서 모든 메시지를 추출하여 하나의 문자열로 결합
    messages = prompt_value.messages
    formatted_text = "\n\n".join([
        f"{msg.type}: {msg.content}" if hasattr(msg, 'type') else str(msg.content)
        for msg in messages
    ])
    return alan_question(formatted_text)

alan_ai_runnable = RunnableLambda(call_alan_with_formatted_prompt)

# 일반 사용자용 프롬프트 템플릿
user_prompt = ChatPromptTemplate.from_messages([
    ("system", """
너는 어릴 때부터 같이 자라온 내 가장 친한 친구야.
항상 반말로 말하고, 너무 가볍지도 너무 진지하지도 않게 설명해.
전문 용어를 쓰더라도 꼭 쉽게 풀어서 말해줘.

너의 역할은 해양 쓰레기 예측 서비스를 돕는 챗봇이야.
사용자가 바다 쓰레기 양, 위험 지역, 변화 추이에 대해 물으면
어렵지 않게, 이해하기 쉬운 말로 설명해줘.

지켜야 할 규칙:
1. 반말만 사용해
2. 모르는 건 모른다고 말해 (추측 금지)
3. 숫자는 항상 단위랑 같이 말해
4. 예측 결과는 "예상", "가능성" 같은 표현을 써
5. 이전 대화(chat_history)를 반드시 참고해서 말해
6. 한 번에 너무 많은 정보를 쏟아내지 마
7. 사용자가 불안해하지 않도록 과장하지 마

너는 전문가가 아니라,
"잘 아는 친구가 옆에서 설명해주는 느낌"이야.
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", """
{input}

답변할 때는:
- 이전 대화 내용이 있으면 자연스럽게 이어서 말하고
- 지역이나 날짜가 이미 나왔으면 다시 묻지 말고 사용해
- 이해 안 될 것 같은 부분은 비유나 예시로 설명해줘
""")
])

# 행정 사용자용 전문가 프롬프트 템플릿
admin_prompt = ChatPromptTemplate.from_messages([
    ("system", """
너는 해양 환경 데이터를 분석하는 행정 지원용 전문가 챗봇이야.
친근한 표현은 쓰지 않고, 객관적이고 명확하게 설명해.
반말은 사용하지 않는다.

너의 역할은 해양 쓰레기 예측 결과를 기반으로
행정 담당자가 의사결정을 할 수 있도록 정보를 정리해주는 것이다.

지켜야 할 규칙:
1. 존댓말과 공식적인 문체 사용
2. 추측이나 감정적 표현 금지
3. 모든 수치는 단위 포함
4. 예측 결과에는 반드시 불확실성 또는 참고사항 명시
5. 이전 대화(chat_history)를 반드시 참고하여 응답
6. 원인 → 결과 → 행정적 시사점 순서로 설명
7. 필요하면 bullet point로 구조화

모델이 예측하지 않은 내용은 생성하지 말고,
데이터 범위를 벗어나면 명확히 한계를 설명하라.
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", """
{input}

답변 가이드:
- 기존 대화에서 이미 언급된 지역/기간/지표는 그대로 활용
- 가능하면 정량적 수치를 우선 제시
- 마지막에 행정적으로 고려할 수 있는 시사점을 포함
""")
])

# Chain 구성: 프롬프트 → Alan AI 호출
user_chat_chain = user_prompt | alan_ai_runnable
admin_chat_chain = admin_prompt | alan_ai_runnable


def get_or_create_memory(session_id: str) -> List[ChatMessage]:
    """세션별 메모리 가져오기 또는 생성"""
    if session_id not in chat_memories:
        chat_memories[session_id] = []
    return chat_memories[session_id]


def format_chat_history(messages: List[ChatMessage]):
    """ChatMessage 리스트를 LangChain 메시지 형식으로 변환"""
    formatted = []
    for msg in messages:
        if msg.role == "user":
            formatted.append(("human", msg.content))
        elif msg.role == "assistant":
            formatted.append(("ai", msg.content))
    return formatted


@router.post("/message/user", response_model=ChatResponse)
async def chat_user(request: ChatRequest):
    """
    일반 사용자용 챗봇 (친근한 반말 톤)
    
    - **message**: 사용자 메시지
    - **session_id**: 세션 ID (대화 기록 유지용, 기본값: "default")
    """
    try:
        # 세션 메모리 가져오기
        memory = get_or_create_memory(request.session_id)
        
        # 이전 대화 내역 포맷팅
        chat_history = format_chat_history(memory[-10:])  # 최근 10개만 사용
        
        # 사용자 메시지 저장
        memory.append(ChatMessage(role="user", content=request.message))
        
        # LangChain을 통한 Alan AI API 호출
        response_text = user_chat_chain.invoke({
            "input": request.message,
            "chat_history": chat_history
        })
        
        # 어시스턴트 응답 저장
        memory.append(ChatMessage(role="assistant", content=response_text))
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {str(e)}")


@router.post("/message/admin", response_model=ChatResponse)
async def chat_admin(request: ChatRequest):
    """
    행정 사용자용 전문가 챗봇 (공식적인 존댓말 톤)
    
    - **message**: 사용자 메시지
    - **session_id**: 세션 ID (대화 기록 유지용, 기본값: "default")
    """
    try:
        # 세션 메모리 가져오기
        memory = get_or_create_memory(request.session_id)
        
        # 이전 대화 내역 포맷팅
        chat_history = format_chat_history(memory[-10:])  # 최근 10개만 사용
        
        # 사용자 메시지 저장
        memory.append(ChatMessage(role="user", content=request.message))
        
        # LangChain을 통한 Alan AI API 호출
        response_text = admin_chat_chain.invoke({
            "input": request.message,
            "chat_history": chat_history
        })
        
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
