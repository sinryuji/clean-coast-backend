"""
특정 기간의 해변 예측 데이터를 생성하는 스크립트

이 스크립트는 get_beach_predictions API를 반복 호출하여
지정된 날짜 범위의 예측 데이터를 생성하고 DB에 저장합니다.

사용법:
    python populate_beach_predictions.py --start 2025-06-01 --end 2025-12-18
    python populate_beach_predictions.py --start 2025-06-01 --end 2025-12-18 --monthly
    python populate_beach_predictions.py  (대화형 모드)
"""
import requests
from datetime import datetime, timedelta
import time
import sys
import argparse

# API 설정
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/trash/beach"


def parse_date(date_string):
    """날짜 문자열을 date 객체로 변환"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 올바르지 않습니다: {date_string}. YYYY-MM-DD 형식을 사용하세요."
        )


def populate_predictions(start_date, end_date):
    """지정된 날짜 범위의 예측 데이터 생성
    
    Args:
        start_date: 시작 날짜 (date 객체)
        end_date: 종료 날짜 (date 객체)
    """
    print(f"데이터 생성 시작: {start_date} ~ {end_date}")
    print(f"총 {(end_date - start_date).days + 1}일 데이터 생성 예정")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        try:
            print(f"\n[{date_str}] API 호출 중...", end=" ")
            
            response = requests.get(
                API_ENDPOINT,
                params={"prediction_date": date_str},
                timeout=300
            )
            
            if response.status_code == 200:
                data = response.json()
                beach_count = len(data)
                print(f"✓ 성공 ({beach_count}개 해변)")
                success_count += 1
                
                # 처음 3개 해변만 출력
                for beach in data[:3]:
                    amount = beach['prediction']['trash_amount']
                    print(f"  - {beach['name']}: {amount:.2f}kg ({beach['status']})")
                if beach_count > 3:
                    print(f"  ... 외 {beach_count - 3}개 해변")
            else:
                print(f"✗ 실패 (HTTP {response.status_code})")
                print(f"  오류: {response.text}")
                fail_count += 1
                
        except requests.exceptions.Timeout:
            print(f"✗ 타임아웃")
            fail_count += 1
        except Exception as e:
            print(f"✗ 오류: {str(e)}")
            fail_count += 1
        
        current_date += timedelta(days=1)
        time.sleep(0.5)
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("데이터 생성 완료!")
    print(f"성공: {success_count}일")
    print(f"실패: {fail_count}일")
    print(f"전체: {success_count + fail_count}일")
    print("=" * 50)


def populate_monthly_first_day(start_date, end_date):
    """지정된 기간 내의 매달 1일 데이터만 생성
    
    Args:
        start_date: 시작 날짜 (date 객체)
        end_date: 종료 날짜 (date 객체)
    """
    print("매달 1일 데이터 생성 시작")
    print(f"기간: {start_date} ~ {end_date}")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    # 시작 월의 1일부터 시작
    current_date = datetime(start_date.year, start_date.month, 1).date()
    end_month = datetime(end_date.year, end_date.month, 1).date()
    
    while current_date <= end_month:
        date_str = current_date.strftime("%Y-%m-%d")
        
        try:
            print(f"\n[{date_str}] API 호출 중...", end=" ")
            
            response = requests.get(
                API_ENDPOINT,
                params={"prediction_date": date_str},
                timeout=300
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 성공 ({len(data)}개 해변)")
                success_count += 1
            else:
                print(f"✗ 실패 (HTTP {response.status_code})")
                fail_count += 1
        except Exception as e:
            print(f"✗ 오류: {str(e)}")
            fail_count += 1
        
        time.sleep(0.5)
        
        # 다음 달 1일로 이동
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1).date()
    
    print(f"\n완료 - 성공: {success_count}, 실패: {fail_count}")


def interactive_mode():
    """대화형 모드"""
    print("=" * 50)
    print("해변 예측 데이터 생성 스크립트 (대화형 모드)")
    print("=" * 50)
    print()
    
    # 시작 날짜 입력
    while True:
        try:
            start_input = input("시작 날짜 (YYYY-MM-DD, 예: 2025-06-01): ").strip()
            start_date = datetime.strptime(start_input, "%Y-%m-%d").date()
            break
        except ValueError:
            print("❌ 잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력하세요.")
    
    # 종료 날짜 입력
    while True:
        try:
            end_input = input("종료 날짜 (YYYY-MM-DD, 예: 2025-12-18): ").strip()
            end_date = datetime.strptime(end_input, "%Y-%m-%d").date()
            
            if end_date < start_date:
                print("❌ 종료 날짜가 시작 날짜보다 이전입니다.")
                continue
            break
        except ValueError:
            print("❌ 잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력하세요.")
    
    days_count = (end_date - start_date).days + 1
    
    print()
    print("=" * 50)
    print(f"시작 날짜: {start_date}")
    print(f"종료 날짜: {end_date}")
    print(f"총 기간: {days_count}일")
    print("=" * 50)
    print()
    
    # 옵션 선택
    print("생성 옵션을 선택하세요:")
    print("1. 전체 날짜 생성 (매일)")
    print("2. 매달 1일만 생성 (빠른 테스트용)")
    print("3. 취소")
    print()
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        confirm = input(
            f"\n약 {days_count}개의 API 호출이 발생합니다. 계속하시겠습니까? (y/n): "
        ).strip().lower()
        if confirm == 'y':
            populate_predictions(start_date, end_date)
        else:
            print("취소되었습니다.")
    elif choice == "2":
        populate_monthly_first_day(start_date, end_date)
    elif choice == "3":
        print("취소되었습니다.")
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="해변 예측 데이터 생성 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 커맨드라인 모드
  python populate_beach_predictions.py --start 2025-06-01 --end 2025-12-18
  python populate_beach_predictions.py --start 2025-06-01 --end 2025-12-18 --monthly
  
  # 대화형 모드
  python populate_beach_predictions.py
        """
    )
    
    parser.add_argument(
        "--start",
        type=parse_date,
        help="시작 날짜 (YYYY-MM-DD 형식)"
    )
    
    parser.add_argument(
        "--end",
        type=parse_date,
        help="종료 날짜 (YYYY-MM-DD 형식)"
    )
    
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="매달 1일만 생성 (빠른 테스트용)"
    )
    
    args = parser.parse_args()
    
    # 커맨드라인 모드
    if args.start and args.end:
        if args.end < args.start:
            print("❌ 종료 날짜가 시작 날짜보다 이전입니다.")
            sys.exit(1)
        
        days_count = (args.end - args.start).days + 1
        
        print("=" * 50)
        print("해변 예측 데이터 생성 스크립트")
        print("=" * 50)
        print(f"시작 날짜: {args.start}")
        print(f"종료 날짜: {args.end}")
        print(f"총 기간: {days_count}일")
        print(f"모드: {'매달 1일만' if args.monthly else '전체 날짜'}")
        print("=" * 50)
        print()
        
        if args.monthly:
            populate_monthly_first_day(args.start, args.end)
        else:
            populate_predictions(args.start, args.end)
    elif args.start or args.end:
        print("❌ --start와 --end를 모두 입력해야 합니다.")
        parser.print_help()
        sys.exit(1)
    else:
        # 대화형 모드
        interactive_mode()
