import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- 설정 부분 (유지보수 강화 버전) ---
REGIONS_CONFIG = [
    {
        "id": "ulsan",
        "name_kr": "울산신용보증재단",
        "url": "https://www.ulsanshinbo.co.kr/02_sinbo/?mcode=0402060000",
        "base_url": "https://www.ulsanshinbo.co.kr"
    },
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

# --- ★★★ 스크래핑 로직 (V4 수정) ★★★ ---
def scrape_announcements_for_region(region):
    """설정된 지역의 '시행중' 공고를 스크래핑하는 범용 함수"""
    try:
        response = requests.get(region["url"], timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: {region['name_kr']} 사이트에 접속할 수 없습니다. ({e})")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    # 새로운 페이지의 테이블 구조에 맞게 선택자 수정
    rows = soup.select("div.board-text table tbody tr")
    
    active_announcements = []
    for row in rows:
        # '시행여부'는 6번째 칸(td)에 위치함
        status_cell = row.select_one("td:nth-of-type(6)")
        
        # '시행중' 이라는 텍스트를 가진 span.ing 태그가 있는지 확인
        if status_cell and status_cell.select_one("span.state.ing"):
            status = status_cell.text.strip()
            
            # '번호'는 1번째 칸, '자금공고명'은 3번째 칸에 위치함
            id_cell = row.select_one("td:nth-of-type(1)")
            title_cell = row.select_one("td:nth-of-type(3) a")

            if id_cell and title_cell:
                active_announcements.append({
                    "id": id_cell.text.strip(),
                    "title": title_cell.text.strip(),
                    # href 속성이 '?mcode=...' 로 시작하므로, region['url']을 기반으로 링크 생성
                    "link": region["url"] + '&' + title_cell['href'].lstrip('?'),
                    "status": status
                })
            
    return active_announcements

# --- DB 및 알림 함수 (이전과 동일) ---
def get_data_from_db(path):
    try:
        return db.reference(path).get()
    except Exception as e: return None

def set_data_to_db(path, data):
    try:
        db.reference(path).set(data)
        print(f"-> DB 경로 '{path}'에 새로운 데이터 저장 성공")
    except Exception as e: print(f"오류: DB 경로 '{path}'에 데이터를 저장하지 못했습니다 - {e}")

def send_fcm_notification(title, body, link, tokens):
    if not tokens: return
    success_count, failure_count = 0, 0
    for token in tokens:
        try:
            message = messaging.Message(data={"title": title, "body": body, "link": link}, token=token)
            messaging.send(message)
            success_count += 1
        except Exception as e:
            print(f"오류: 토큰 [{token[:20]}...] 발송 실패 - {e}")
            failure_count += 1
    print(f"-> 알림 발송 결과: 성공 {success_count}건, 실패 {failure_count}건")

# --- 메인 로직 (이전과 동일) ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 전체 지역 지원사업 공고 확인을 시작합니다...")
    if not initialize_fcm(): exit()

    all_tokens = get_data_from_db('tokens')
    tokens_list = list(all_tokens.keys()) if all_tokens else []

    for region in REGIONS_CONFIG:
        region_id, region_name_kr = region["id"], region["name_kr"]
        db_path = f'announcements/{region_id}'
        print(f"\n--- {region_name_kr} 작업 시작 ---")

        scraped_data = scrape_announcements_for_region(region)
        print(f"-> 스크래핑 완료: 총 {len(scraped_data)}개의 '시행중' 공고 발견")

        db_data = get_data_from_db(db_path) or []
        scraped_ids = {item['id'] for item in scraped_data}
        db_ids = {item['id'] for item in db_data}
        new_item_ids = scraped_ids - db_ids

        if new_item_ids:
            print(f"-> ★★★ {len(new_item_ids)}개의 새로운 공고 발견! 알림 발송 ★★★")
            if tokens_list:
                for new_id in new_item_ids:
                    new_item = next((item for item in scraped_data if item["id"] == new_id), None)
                    if new_item:
                        send_fcm_notification(f"[{region_name_kr}] 신규 지원사업", new_item['title'], new_item['link'], tokens_list)
            else:
                print("-> 알림을 보낼 사용자가 없습니다.")
        else:
            print("-> 새로운 공고가 없습니다.")
        set_data_to_db(db_path, scraped_data)
    print("\n--- 모든 작업 종료 ---")
