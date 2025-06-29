import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- 설정 부분 (이전과 동일) ---
NOTICE_URL = "https://www.ulsanshinbo.co.kr/04_notice/?mcode=0404010000"
BASE_URL = "https://www.ulsanshinbo.co.kr"
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
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        print("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        print(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False

# --- DB 연동 함수들 (이전과 동일) ---
def get_last_sent_id_from_db():
    try:
        ref = db.reference('state/last_post_id')
        return ref.get()
    except Exception as e:
        print(f"오류: DB에서 마지막 ID를 읽지 못했습니다 - {e}")
        return None

def save_id_to_db(post_id):
    try:
        ref = db.reference('state')
        ref.set({'last_post_id': post_id})
        print(f"-> DB에 새로운 ID 저장 성공: {post_id}")
    except Exception as e:
        print(f"오류: DB에 ID를 저장하지 못했습니다 - {e}")

def get_all_tokens_from_db():
    try:
        ref = db.reference('tokens') 
        tokens_dict = ref.get()
        if not tokens_dict:
            print("-> DB에 저장된 웹 푸시 토큰이 없습니다.")
            return []
        return list(tokens_dict.keys())
    except Exception as e:
        print(f"오류: DB에서 토큰을 읽지 못했습니다 - {e}")
        return []

# --- ★★★ 알림 발송 함수 (수정됨) ★★★ ---
def send_fcm_to_each_token(title, body, link, tokens):
    """
    (수정된 방식) 여러 토큰에 각각 하나씩 알림을 보냅니다.
    Multicast(일괄 발송) 대신 Send(개별 발송)를 사용합니다.
    """
    if not tokens:
        return

    print(f"-> 총 {len(tokens)}개의 토큰에 개별 발송을 시도합니다...")
    success_count = 0
    failure_count = 0

    # 각 토큰에 대해 루프를 돌면서 개별적으로 메시지 발송
    for token in tokens:
        try:
            # 개별 발송에는 Message 객체를 사용합니다.
            message = messaging.Message(
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                    ),
                    fcm_options=messaging.WebpushFCMOptions(
                        link=link
                    ),
                ),
                token=token, # 개별 토큰 지정
            )
            messaging.send(message)
            success_count += 1
        except Exception as e:
            # 특정 토큰 발송 실패 시 로그를 남기고 계속 진행
            print(f"오류: 토큰 [{token[:20]}...] 발송 실패 - {e}")
            failure_count += 1
    
    print(f"-> 개별 발송 결과: 성공 {success_count}건, 실패 {failure_count}건")


def get_latest_post_info():
    """웹사이트에서 최신 공지사항 정보를 가져오는 함수 (이전과 동일)"""
    try:
        response = requests.get(NOTICE_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: 웹사이트에 접속할 수 없습니다. ({e}")
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


# --- ★★★ 메인 실행 로직 (수정됨) ★★★ ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 신규 공지사항 확인을 시작합니다...")

    if not initialize_fcm():
        exit()

    latest_post_num, latest_title, latest_link = get_latest_post_info()

    if not latest_post_num:
        print("-> 최신 게시물 정보를 가져오는 데 실패했습니다.")
    else:
        last_sent_id = get_last_sent_id_from_db()
        
        print(f"-> 웹사이트 최신 ID: {latest_post_num}")
        print(f"-> DB에 저장된 마지막 ID: {last_sent_id or '없음'}")

        if str(latest_post_num) != str(last_sent_id):
            print("\n★★★ 새로운 공지사항 발견! 웹 푸시 알림을 발송합니다. ★★★")
            print(f"  - 번호: {latest_post_num}")
            print(f"  - 제목: {latest_title}")
            
            all_tokens = get_all_tokens_from_db()

            if all_tokens:
                # 수정된 개별 발송 함수를 호출합니다.
                send_fcm_to_each_token(
                    title="새 공지사항 알림",
                    body=latest_title,
                    link=latest_link,
                    tokens=all_tokens
                )
            
            save_id_to_db(latest_post_num)
        else:
            print("-> 새로운 공지사항이 없습니다. 알림을 발송하지 않습니다.")
    
    print("\n작업을 종료합니다.")
