from sqlalchemy import Column, Integer, String, Float
from core.database import Base


class Beach(Base):
    __tablename__ = "beaches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(String(200), nullable=True)
    
    def __repr__(self):
        return f"<Beach(name='{self.name}', latitude={self.latitude}, longitude={self.longitude})>"
