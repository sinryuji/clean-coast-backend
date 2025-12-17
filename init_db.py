"""
데이터베이스 초기화 스크립트

이 스크립트를 실행하면:
1. 데이터베이스 테이블을 생성합니다
2. 초기 관리자 계정을 생성합니다
"""
import sys
from core.database import init_db, SessionLocal
from models.user import User
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
            
    except Exception as e:
        print(f"오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_users()
