import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- 설정 부분 ---
NOTICE_URL = "https://www.ulsanshinbo.co.kr/04_notice/?mcode=0404010000"
BASE_URL = "https://www.ulsanshinbo.co.kr"
FCM_TOPIC = "new_notice"

# !!! 중요 !!! 1단계에서 복사한 자신의 Realtime Database URL을 여기에 붙여넣으세요.
DATABASE_URL = 'https://shinbo-notify-default-rtdb.asia-southeast1.firebasedatabase.app/' 

def initialize_fcm():
    """FCM 및 DB 초기화 함수"""
    try:
        firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        if not firebase_credentials_json:
            print("오류: FIREBASE_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다.")
            return False

        cred_json = json.loads(firebase_credentials_json)
        cred = credentials.Certificate(cred_json)
        
        # 이미 초기화되었는지 확인 (GitHub Actions 환경에서 여러번 실행될 수 있음)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': DATABASE_URL
            })
        print("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        print(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False

# --- Firebase DB 연동 함수 ---
def get_last_sent_id_from_db():
    """DB에서 마지막으로 보낸 공지사항 ID를 가져옵니다."""
    try:
        ref = db.reference('state/last_post_id')
        return ref.get()
    except Exception as e:
        print(f"오류: DB에서 마지막 ID를 읽지 못했습니다 - {e}")
        return None

def save_id_to_db(post_id):
    """새로운 공지사항 ID를 DB에 저장(덮어쓰기)합니다."""
    try:
        ref = db.reference('state')
        ref.set({'last_post_id': post_id})
        print(f"-> DB에 새로운 ID 저장 성공: {post_id}")
    except Exception as e:
        print(f"오류: DB에 ID를 저장하지 못했습니다 - {e}")

# --- 기존 함수들 (send_fcm_notification, get_latest_post_info) ---
def send_fcm_notification(title, body, link):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={'link': link},
            topic=FCM_TOPIC,
        )
        response = messaging.send(message)
        print(f"-> FCM 메시지 발송 성공: {response}")
    except Exception as e:
        print(f"오류: FCM 메시지 발송 실패 - {e}")

def get_latest_post_info():
    try:
        response = requests.get(NOTICE_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: 웹사이트에 접속할 수 없습니다. ({e})")
        return None, None, None
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("div.board-text table tbody tr")
    for row in rows:
        if 'ntc' in row.get('class', []):
            continue
        post_number_td = row.select_one("td.num")
        if not post_number_td:
            continue
        post_number = post_number_td.text.strip()
        subject_td_link = row.select_one("td.link a")
        if subject_td_link:
            title = subject_td_link.text.strip()
            relative_link = subject_td_link['href']
            full_link = BASE_URL + relative_link
            return post_number, title, full_link
    return None, None, None

# --- 메인 실행 로직 (수정됨) ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 신규 공지사항 확인을 시작합니다...")

    if not initialize_fcm():
        exit()

    latest_post_num, latest_title, latest_link = get_latest_post_info()

    if not latest_post_num:
        print("-> 최신 게시물 정보를 가져오는 데 실패했습니다.")
    else:
        # DB에서 마지막으로 보낸 ID를 가져옴
        last_sent_id = get_last_sent_id_from_db()
        
        print(f"-> 웹사이트 최신 ID: {latest_post_num}")
        print(f"-> DB에 저장된 마지막 ID: {last_sent_id or '없음'}")

        # 웹사이트 최신 ID와 DB에 저장된 ID를 비교
        if str(latest_post_num) != str(last_sent_id):
            print("\n★★★ 새로운 공지사항 발견! 알림을 발송합니다. ★★★")
            print(f"  - 번호: {latest_post_num}")
            print(f"  - 제목: {latest_title}")
            
            # 1. FCM 알림 발송
            send_fcm_notification(
                title="새 공지사항 알림",
                body=latest_title,
                link=latest_link
            )
            
            # 2. 새로 보낸 ID를 DB에 저장
            save_id_to_db(latest_post_num)
        else:
            print("-> 새로운 공지사항이 없습니다. 알림을 발송하지 않습니다.")
    
    print("\n작업을 종료합니다.")