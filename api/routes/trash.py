from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from datetime import datetime, date
from sqlalchemy.orm import Session
from fetch import fetchers
from enum import Enum
import numpy as np
from core.predict import predict_by_vector
from core.database import get_db
from models.beach_prediction import BeachPrediction
from models.beach import Beach
import os

router = APIRouter(
    prefix="/v1/trash",
    tags=["trash"]
)


class TrashStatus(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Location(BaseModel):
    latitude: float
    longitude: float


class Prediction(BaseModel):
    trash_amount: float


class PredictResponse(BaseModel):
    date: str
    location: Location
    prediction: Prediction
    status: TrashStatus


class BeachPredictionResponse(BaseModel):
    name: str
    date: str
    location: Location
    prediction: Prediction
    status: TrashStatus
    temperature: float


def calculate_trash_prediction(date_obj: datetime, latitude: float, longitude: float) -> tuple[float, TrashStatus]:
    """
    주어진 날짜와 위치에 대한 쓰레기 양을 예측합니다.
    
    Args:
        date_obj: 예측 날짜
        latitude: 위도
        longitude: 경도
    
    Returns:
        (trash_amount, status) 튜플
    """
    # 해류 및 풍속 데이터 가져오기
    current_dir, current_speed = fetchers.fetch_current(date_obj, latitude, longitude)
    wind_dir, wind_speed = fetchers.fetch_wind(date_obj, latitude, longitude)

    # 벡터 계산
    rad = np.deg2rad(current_dir)
    current_u = current_speed * np.cos(rad)
    current_v = current_speed * np.sin(rad)

    rad = np.deg2rad(wind_dir)
    wind_u = wind_speed * np.cos(rad)
    wind_v = wind_speed * np.sin(rad)

    # 날짜 feature 계산
    dayofyear = date_obj.timetuple().tm_yday
    day_sin = np.sin(2 * np.pi * dayofyear / 365)
    day_cos = np.cos(2 * np.pi * dayofyear / 365)
    
    print(f'Features - dayofyear: {dayofyear}, day_sin: {day_sin:.4f}, day_cos: {day_cos:.4f}, '
          f'wind_speed: {wind_speed:.2f}, current_speed: {current_speed:.2f}, '
          f'wind_u: {wind_u:.2f}, wind_v: {wind_v:.2f}, current_u: {current_u:.2f}, current_v: {current_v:.2f}')
    
    # trash_amount 예측
    trash_amount = predict_by_vector(
        model_path=os.environ.get('MODEL_PATH'),
        dayofyear=dayofyear,
        day_sin=day_sin,
        day_cos=day_cos,
        wind_speed=wind_speed,
        current_speed=current_speed,
        wind_u=wind_u,
        wind_v=wind_v,
        current_u=current_u,
        current_v=current_v
    )
    
    # status 결정
    if trash_amount < 200:
        status = TrashStatus.LOW
    elif trash_amount < 300:
        status = TrashStatus.MEDIUM
    else:
        status = TrashStatus.HIGH
    
    return trash_amount, status


@router.get("/predict", response_model=PredictResponse)
async def get_prediction(
    date: str = Query(
        ..., 
        description="날짜 및 시간 (ISO 8601 형식)",
        example="2016-01-05T15:20:00"
    ),
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
        description="위도 (-90 ~ 90)",
        example=33.4507
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
        description="경도 (-180 ~ 180)",
        example=126.5707
    )
):
    """
    쓰레기 양 예측 데이터를 조회합니다.
    
    - **date**: 날짜 및 시간 (ISO 8601 형식, 예: "2016-01-05T15:20:00")
    - **latitude**: 위도 (-90 ~ 90)
    - **longitude**: 경도 (-180 ~ 180)
    """
    try:
        # ISO 8601 형식 날짜 파싱
        date_obj = datetime.fromisoformat(date)
        
        # 쓰레기 양 예측
        trash_amount, status = calculate_trash_prediction(date_obj, latitude, longitude)
        
        return PredictResponse(
            date=date_obj.strftime("%Y-%m-%d"),
            location=Location(
                latitude=latitude,
                longitude=longitude
            ),
            prediction=Prediction(
                trash_amount=trash_amount
            ),
            status=status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"날짜 형식이 올바르지 않습니다 (ISO 8601 형식 필요): {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beach", response_model=list[BeachPredictionResponse])
async def get_beach_predictions(
    prediction_date: str = Query(
        None,
        description="예측 날짜 (YYYY-MM-DD 형식). 미지정시 오늘 날짜 사용",
        example="2024-01-15"
    ),
    db: Session = Depends(get_db)
):
    """
    제주도 주요 해변의 쓰레기 양 예측 데이터를 조회합니다.
    
    11개 해변의 지정된 날짜 기준 쓰레기 예측량을 반환합니다.
    DB에 해당 날짜 데이터가 있으면 DB에서 조회하고, 없으면 API 호출 후 저장합니다.
    
    - **prediction_date**: 예측 날짜 (YYYY-MM-DD 형식, 선택 사항. 미지정시 오늘 날짜)
    """
    try:
        # 날짜 파싱
        if prediction_date:
            try:
                target_date = datetime.strptime(prediction_date, "%Y-%m-%d").date()
                date_obj = datetime.strptime(prediction_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD 형식 필요)")
        else:
            target_date = date.today()
            date_obj = datetime.now()
        
        # DB에서 모든 해변 정보 조회
        beaches = db.query(Beach).all()
        if not beaches:
            raise Exception("DB에 해변 정보가 없습니다. init_db.py를 실행하여 초기 데이터를 생성하세요.")
        
        # DB에서 지정된 날짜의 모든 해변 데이터 조회
        cached_predictions = db.query(BeachPrediction).filter(
            BeachPrediction.prediction_date == target_date
        ).all()
        
        # DB에 모든 해변 데이터가 있는지 확인
        cached_beach_names = {pred.beach_name for pred in cached_predictions}
        all_beach_names = {beach.name for beach in beaches}
        
        results = []
        
        # DB에 모든 데이터가 있으면 DB에서 반환
        if cached_beach_names == all_beach_names:
            print(f"DB에서 {target_date} 날짜 데이터 조회")
            for pred in cached_predictions:
                results.append(BeachPredictionResponse(
                    name=pred.beach_name,
                    date=pred.prediction_date.strftime("%Y-%m-%d"),
                    location=Location(
                        latitude=pred.latitude,
                        longitude=pred.longitude
                    ),
                    prediction=Prediction(
                        trash_amount=pred.trash_amount
                    ),
                    status=TrashStatus(pred.status),
                    temperature=pred.temperature if pred.temperature else 0.0
                ))
        else:
            # DB에 데이터가 없거나 불완전하면 API 호출 후 저장
            print(f"API 호출하여 {target_date} 날짜 데이터 생성")
            
            # 기존 날짜 데이터 삭제 (불완전한 데이터 방지)
            db.query(BeachPrediction).filter(
                BeachPrediction.prediction_date == target_date
            ).delete()
            
            for beach in beaches:
                try:
                    latitude = beach.latitude
                    longitude = beach.longitude
                    
                    # 쓰레기 양 예측
                    trash_amount, status = calculate_trash_prediction(date_obj, latitude, longitude)
                    
                    # 수온 데이터 가져오기
                    try:
                        temperature = fetchers.fetch_temperature(date_obj, latitude, longitude)
                    except Exception as temp_error:
                        print(f"수온 데이터 조회 실패 ({beach.name}): {str(temp_error)}")
                        temperature = None
                    
                    # DB에 저장
                    beach_prediction = BeachPrediction(
                        beach_name=beach.name,
                        prediction_date=target_date,
                        latitude=latitude,
                        longitude=longitude,
                        trash_amount=trash_amount,
                        status=status.value,
                        temperature=temperature
                    )
                    db.add(beach_prediction)
                    
                    # 결과 리스트에 추가
                    results.append(BeachPredictionResponse(
                        name=beach.name,
                        date=target_date.strftime("%Y-%m-%d"),
                        location=Location(
                            latitude=latitude,
                            longitude=longitude
                        ),
                        prediction=Prediction(
                            trash_amount=trash_amount
                        ),
                        status=status,
                        temperature=temperature if temperature else 0.0
                    ))
                    
                except Exception as beach_error:
                    # 개별 해변 에러는 로깅만 하고 계속 진행
                    print(f"해변 {beach.name} 예측 실패: {str(beach_error)}")
                    continue
            
            # DB에 커밋
            db.commit()
        
        if not results:
            raise Exception("모든 해변 예측에 실패했습니다")
        
        return results
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
