import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- ★★★ 설정 부분 (가장 중요) ★★★ ---
# 나중에 다른 지역을 추가할 때, 이 리스트에 정보만 추가하면 됩니다.
REGIONS_CONFIG = [
    {
        "id": "ulsan",
        "name_kr": "울산신용보증재단",
        "url": "https://www.ulsanshinbo.co.kr/02_sinbo/?mcode=0402060000",
        "base_url": "https://www.ulsanshinbo.co.kr"
    },
    # 예시: 나중에 부산을 추가하고 싶다면 아래 주석을 풀고 정보만 채우면 됩니다.
    # {
    #     "id": "busan",
    #     "name_kr": "부산신용보증재단",
    #     "url": "https://www.busansinbo.or.kr/...",
    #     "base_url": "https://www.busansinbo.or.kr"
    # }
]

DATABASE_URL = 'https://shinbo-notify-default-rtdb.asia-southeast1.firebasedatabase.app/' 

def initialize_fcm():
    """FCM 및 DB 초기화 함수"""
    try:
        if not firebase_admin._apps:
            firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
            if not firebase_credentials_json:
                raise ValueError("FIREBASE_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다.")
            cred_json = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        print("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        print(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False

# --- 데이터베이스 및 스크래핑 로직 (유지보수 강화) ---

def scrape_announcements_for_region(region):
    """설정된 지역의 '시행중' 공고를 스크래핑하는 범용 함수"""
    try:
        response = requests.get(region["url"], timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: {region['name_kr']} 사이트에 접속할 수 없습니다. ({e})")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    # 울산신보 '중소기업지원자금공고' 페이지의 테이블 구조에 맞춤
    rows = soup.select("div.board-text table tbody tr")
    
    active_announcements = []
    for row in rows:
        # 5번째 칸(td)에서 상태(status) 텍스트를 가져옴
        status_td = row.select_one("td:nth-of-type(5)")
        # '시행중' 이라는 텍스트가 포함된 경우에만 데이터를 수집
        if not status_td or "시행중" not in status_td.text:
            continue
        
        post_id_td = row.select_one("td.num")
        title_link_td = row.select_one("td.link a")

        if post_id_td and title_link_td:
            active_announcements.append({
                "id": post_id_td.text.strip(),
                "title": title_link_td.text.strip(),
                "link": region["base_url"] + title_link_td['href'],
                "status": status_td.text.strip()
            })
            
    return active_announcements

def get_data_from_db(path):
    """DB의 특정 경로에서 데이터를 가져오는 범용 함수"""
    try:
        return db.reference(path).get()
    except Exception as e:
        print(f"오류: DB 경로 '{path}'에서 데이터를 읽지 못했습니다 - {e}")
        return None

def set_data_to_db(path, data):
    """DB의 특정 경로에 데이터를 저장하는 범용 함수"""
    try:
        db.reference(path).set(data)
        print(f"-> DB 경로 '{path}'에 새로운 데이터 저장 성공")
    except Exception as e:
        print(f"오류: DB 경로 '{path}'에 데이터를 저장하지 못했습니다 - {e}")

def send_fcm_notification(title, body, link, tokens):
    """개별 토큰에 알림을 보내는 함수"""
    if not tokens:
        return
    
    success_count = 0
    failure_count = 0
    for token in tokens:
        try:
            message = messaging.Message(
                data={"title": title, "body": body, "link": link},
                token=token,
            )
            messaging.send(message)
            success_count += 1
        except Exception as e:
            print(f"오류: 토큰 [{token[:20]}...] 발송 실패 - {e}")
            failure_count += 1
    print(f"-> 알림 발송 결과: 성공 {success_count}건, 실패 {failure_count}건")


# --- 메인 실행 로직 (유지보수 강화) ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 전체 지역 지원사업 공고 확인을 시작합니다...")

    if not initialize_fcm():
        exit()

    all_tokens = get_data_from_db('tokens')
    tokens_list = list(all_tokens.keys()) if all_tokens else []

    # 설정된 모든 지역에 대해 순차적으로 작업 수행
    for region in REGIONS_CONFIG:
        region_id = region["id"]
        region_name_kr = region["name_kr"]
        db_path = f'announcements/{region_id}'
        
        print(f"\n--- {region_name_kr} 작업 시작 ---")

        # 1. 해당 지역의 '시행중' 공고 스크래핑
        scraped_data = scrape_announcements_for_region(region)
        print(f"-> 스크래핑 완료: 총 {len(scraped_data)}개의 '시행중' 공고 발견")

        # 2. DB에서 이전 데이터 가져오기
        db_data = get_data_from_db(db_path) or []
        
        scraped_ids = {item['id'] for item in scraped_data}
        db_ids = {item['id'] for item in db_data}

        # 3. 새로운 공고 확인 및 알림 발송
        new_item_ids = scraped_ids - db_ids
        if new_item_ids:
            print(f"-> ★★★ {len(new_item_ids)}개의 새로운 공고 발견! 알림 발송 ★★★")
            if tokens_list:
                for new_id in new_item_ids:
                    new_item = next((item for item in scraped_data if item["id"] == new_id), None)
                    if new_item:
                        notification_title = f"[{region_name_kr}] 신규 지원사업"
                        notification_body = new_item['title']
                        print(f"  - 알림 발송: {notification_body}")
                        send_fcm_notification(notification_title, notification_body, new_item['link'], tokens_list)
            else:
                print("-> 알림을 보낼 사용자가 없습니다.")
        else:
            print("-> 새로운 공고가 없습니다.")

        # 4. 최신 정보로 DB 업데이트
        set_data_to_db(db_path, scraped_data)

    print("\n--- 모든 작업 종료 ---")
