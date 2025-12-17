"""
데이터베이스 초기화 스크립트

이 스크립트를 실행하면:
1. 데이터베이스 테이블을 생성합니다
2. 초기 관리자 계정을 생성합니다
3. 제주도 해변 정보를 생성합니다
"""
import sys
from core.database import init_db, SessionLocal
from models.user import User
from models.beach import Beach
from models.beach_prediction import BeachPrediction
from passlib.context import CryptContext

# bcrypt 설정 (rounds를 12로 설정하여 안전성 확보)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def create_initial_users():
    """초기 사용자 생성"""
    db = SessionLocal()
    
    try:
        # 테이블 생성
        print("데이터베이스 테이블 생성 중...")
        init_db()
        print("테이블 생성 완료!")
        
        # admin 계정이 없으면 생성
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("관리자 계정 생성 중...")
            
            # 비밀번호 해싱 시도
            try:
                hashed_password = pwd_context.hash("admin123")
                admin = User(
                    username="admin",
                    password=hashed_password,
                    email="admin@example.com"
                )
                db.add(admin)
                db.commit()
                print("관리자 계정 생성 완료! (username: admin, password: admin123)")
            except Exception as hash_error:
                print(f"비밀번호 해싱 오류: {hash_error}")
                print("bcrypt 라이브러리를 재설치해주세요:")
                print("  pip uninstall bcrypt passlib")
                print("  pip install bcrypt==4.0.1 passlib==1.7.4")
                raise
        else:
            print("관리자 계정이 이미 존재합니다.")
        
        # test 계정 생성
        test_user = db.query(User).filter(User.username == "test").first()
        if not test_user:
            print("테스트 계정 생성 중...")
            try:
                hashed_password = pwd_context.hash("test123")
                test = User(
                    username="test",
                    password=hashed_password,
                    email="test@example.com"
                )
                db.add(test)
                db.commit()
                print("테스트 계정 생성 완료! (username: test, password: test123)")
            except Exception as hash_error:
                print(f"비밀번호 해싱 오류: {hash_error}")
                raise
        else:
            print("테스트 계정이 이미 존재합니다.")
        
        # 해변 데이터 생성
        print("\n제주도 해변 데이터 확인 중...")
        beaches_data = [
            {"name": "AEWOL", "latitude": 33.44639, "longitude": 126.29343, "description": "애월해안(곽지과물해변)"},
            {"name": "JOCHEON", "latitude": 33.54323, "longitude": 126.66986, "description": "조천해안(함덕해수욕장)"},
            {"name": "YERAE", "latitude": 33.22843, "longitude": 126.47737, "description": "예래해안(강정크루즈터미널)"},
            {"name": "HALLIM", "latitude": 33.39511, "longitude": 126.24028, "description": "한림해안(협재해수욕장)"},
            {"name": "SEONGSAN", "latitude": 33.47330, "longitude": 126.93454, "description": "성산해안(성산항)"},
            {"name": "JUNGMUN", "latitude": 33.24421, "longitude": 126.41406, "description": "중문해안(중문색달해수욕장)"},
            {"name": "GUJWA", "latitude": 33.55565, "longitude": 126.79566, "description": "구좌해안(월정리해변)"},
            {"name": "PYOSEON", "latitude": 33.32585, "longitude": 126.84252, "description": "표선해안(표선해비치해변)"},
            {"name": "ANDEOK", "latitude": 33.23000, "longitude": 126.29500, "description": "안덕해안(사계해변)"},
            {"name": "NAMWON", "latitude": 33.27262, "longitude": 126.66034, "description": "남원해안(위미항)"},
            {"name": "DAEJEONG", "latitude": 33.21641, "longitude": 126.25031, "description": "대정해안(모슬포항)"}
        ]
        
        existing_beaches = db.query(Beach).count()
        if existing_beaches == 0:
            print("해변 데이터 생성 중...")
            for beach_data in beaches_data:
                beach = Beach(**beach_data)
                db.add(beach)
            db.commit()
            print(f"{len(beaches_data)}개 해변 데이터 생성 완료!")
        else:
            print(f"해변 데이터가 이미 존재합니다. (총 {existing_beaches}개)")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_users()
