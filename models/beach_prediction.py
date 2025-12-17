from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from datetime import datetime
from core.database import Base


class BeachPrediction(Base):
    __tablename__ = "beach_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    beach_name = Column(String(50), nullable=False, index=True)
    prediction_date = Column(Date, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    trash_amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    current_dir = Column(Float, nullable=True)
    current_speed = Column(Float, nullable=True)
    wind_dir = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BeachPrediction(beach_name='{self.beach_name}', date='{self.prediction_date}', trash_amount={self.trash_amount})>"
