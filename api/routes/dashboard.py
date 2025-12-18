from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from core.database import get_db
from models.beach_prediction import BeachPrediction
from models.beach import Beach
from typing import List
from enum import Enum

router = APIRouter(
    prefix="/v1/dashboard",
    tags=["dashboard"]
)


class RiskLevel(str, Enum):
    HIGH = "높음"
    MEDIUM = "중간"
    LOW = "낮음"


class ActionType(str, Enum):
    IMMEDIATE = "즉시 수거"
    MONITOR = "모니터링 강화"
    REGULAR = "정기 점검"
    WATCH = "주의 관찰"


class MonthlySummary(BaseModel):
    total_predicted_amount: float  # 총 예상 유입량 (kg)
    previous_month_change: float  # 전월 대비 변화율 (%)
    high_risk_count: int  # 위험 지역 수
    medium_risk_count: int  # 주의 지역 수
    immediate_action_count: int  # 즉시 조치 필요 수
    regular_check_count: int  # 정기 점검 수


class MonthlyTrend(BaseModel):
    month: str  # "Jul", "Aug", "Sep", etc.
    year: int
    total_amount: float  # kg


class RiskArea(BaseModel):
    beach_name: str  # 지역명
    predicted_amount: float  # 예상량 (kg)
    risk_level: RiskLevel  # 위험도
    action_required: ActionType  # 조치사항
    latitude: float
    longitude: float


class DashboardResponse(BaseModel):
    target_month: str  # "2025-12"
    summary: MonthlySummary
    monthly_trends: List[MonthlyTrend]
    risk_areas: List[RiskArea]


def calculate_risk_level(trash_amount: float) -> RiskLevel:
    """쓰레기 양에 따른 위험도 계산"""
    if trash_amount >= 400:
        return RiskLevel.HIGH
    elif trash_amount >= 250:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def calculate_action_type(trash_amount: float) -> ActionType:
    """쓰레기 양에 따른 조치사항 결정"""
    if trash_amount >= 400:
        return ActionType.IMMEDIATE
    elif trash_amount >= 300:
        return ActionType.MONITOR
    elif trash_amount >= 200:
        return ActionType.REGULAR
    else:
        return ActionType.WATCH


@router.get("", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    행정 대시보드 데이터를 조회합니다.
    
    현재 월 기준으로:
    - 월간 요약 통계 (총 예상 유입량, 전월 대비, 위험 지역 현황 등)
    - 최근 6개월 월별 추이
    - 위험 지역 목록 (높은 순서대로)
    """
    try:
        # 현재 날짜 기준
        today = date.today()
        current_year = today.year
        current_month = today.month
        
        # 이번 달 첫째 날
        first_day_of_month = date(current_year, current_month, 1)
        
        # 지난 달 첫째 날과 마지막 날
        if current_month == 1:
            last_month_year = current_year - 1
            last_month = 12
        else:
            last_month_year = current_year
            last_month = current_month - 1
        first_day_of_last_month = date(last_month_year, last_month, 1)
        last_day_of_last_month = first_day_of_month - timedelta(days=1)
        
        # 1. 이번 달 데이터 집계
        current_month_data = db.query(
            func.sum(BeachPrediction.trash_amount).label('total'),
            func.count(BeachPrediction.id).label('count')
        ).filter(
            extract('year', BeachPrediction.prediction_date) == current_year,
            extract('month', BeachPrediction.prediction_date) == current_month
        ).first()
        
        current_total = float(current_month_data.total) if current_month_data.total else 0.0
        
        # 2. 지난 달 데이터 집계
        last_month_data = db.query(
            func.sum(BeachPrediction.trash_amount).label('total')
        ).filter(
            BeachPrediction.prediction_date >= first_day_of_last_month,
            BeachPrediction.prediction_date <= last_day_of_last_month
        ).first()
        
        last_month_total = float(last_month_data.total) if last_month_data.total else 0.0
        
        # 전월 대비 변화율 계산
        if last_month_total > 0:
            change_rate = ((current_total - last_month_total) / last_month_total) * 100
        else:
            change_rate = 0.0
        
        # 3. 이번 달 위험 지역 분석 (각 해변별 최신 데이터)
        # 각 해변의 이번 달 최신 예측 데이터 가져오기
        subquery = db.query(
            BeachPrediction.beach_name,
            func.max(BeachPrediction.prediction_date).label('max_date')
        ).filter(
            extract('year', BeachPrediction.prediction_date) == current_year,
            extract('month', BeachPrediction.prediction_date) == current_month
        ).group_by(BeachPrediction.beach_name).subquery()
        
        current_predictions = db.query(BeachPrediction).join(
            subquery,
            (BeachPrediction.beach_name == subquery.c.beach_name) &
            (BeachPrediction.prediction_date == subquery.c.max_date)
        ).all()
        
        # 위험도별 카운트
        high_risk_count = 0
        medium_risk_count = 0
        immediate_action_count = 0
        regular_check_count = 0
        
        risk_areas = []
        
        for pred in current_predictions:
            risk_level = calculate_risk_level(pred.trash_amount)
            action_type = calculate_action_type(pred.trash_amount)
            
            if risk_level == RiskLevel.HIGH:
                high_risk_count += 1
            elif risk_level == RiskLevel.MEDIUM:
                medium_risk_count += 1
            
            if action_type == ActionType.IMMEDIATE:
                immediate_action_count += 1
            elif action_type in [ActionType.REGULAR, ActionType.WATCH]:
                regular_check_count += 1
            
            risk_areas.append(RiskArea(
                beach_name=pred.beach_name,
                predicted_amount=pred.trash_amount,
                risk_level=risk_level,
                action_required=action_type,
                latitude=pred.latitude,
                longitude=pred.longitude
            ))
        
        # 위험도 순으로 정렬 (쓰레기 양 많은 순)
        risk_areas.sort(key=lambda x: x.predicted_amount, reverse=True)
        
        # 4. 최근 6개월 월별 추이
        monthly_trends = []
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        for i in range(5, -1, -1):  # 6개월 전부터 현재까지
            target_date = today - timedelta(days=30*i)  # 대략적인 계산
            target_year = target_date.year
            target_month = target_date.month
            
            month_data = db.query(
                func.sum(BeachPrediction.trash_amount).label('total')
            ).filter(
                extract('year', BeachPrediction.prediction_date) == target_year,
                extract('month', BeachPrediction.prediction_date) == target_month
            ).first()
            
            month_total = float(month_data.total) if month_data.total else 0.0
            
            monthly_trends.append(MonthlyTrend(
                month=month_names[target_month - 1],
                year=target_year,
                total_amount=round(month_total, 2)
            ))
        
        # 5. 응답 구성
        summary = MonthlySummary(
            total_predicted_amount=round(current_total, 2),
            previous_month_change=round(change_rate, 1),
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            immediate_action_count=immediate_action_count,
            regular_check_count=regular_check_count
        )
        
        response = DashboardResponse(
            target_month=f"{current_year}-{current_month:02d}",
            summary=summary,
            monthly_trends=monthly_trends,
            risk_areas=risk_areas
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")
