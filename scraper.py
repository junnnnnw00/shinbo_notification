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

# 사용자의 데이터베이스 URL을 그대로 사용합니다.
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
        
        # 이미 초기화되었는지 확인
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': DATABASE_URL
            })
        print("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        print(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False

# --- Firebase DB 연동 함수 (수정됨) ---

def get_last_sent_id_from_db():
    """DB에서 마지막으로 보낸 공지사항 ID를 가져옵니다."""
    try:
        # 경로는 이전과 동일 ('state/last_post_id')
        ref = db.reference('state/last_post_id')
        return ref.get()
    except Exception as e:
        print(f"오류: DB에서 마지막 ID를 읽지 못했습니다 - {e}")
        return None

def save_id_to_db(post_id):
    """새로운 공지사항 ID를 DB에 저장합니다."""
    try:
        ref = db.reference('state')
        ref.set({'last_post_id': post_id})
        print(f"-> DB에 새로운 ID 저장 성공: {post_id}")
    except Exception as e:
        print(f"오류: DB에 ID를 저장하지 못했습니다 - {e}")

# --- 웹 푸시를 위한 새로운 함수들 ---

def get_all_tokens_from_db():
    """DB에서 모든 웹 브라우저 토큰을 가져옵니다."""
    try:
        # 웹 페이지에서 저장한 토큰들이 있는 경로를 지정합니다. 예: '/tokens'
        ref = db.reference('tokens') 
        tokens_dict = ref.get()
        if not tokens_dict:
            print("-> DB에 저장된 웹 푸시 토큰이 없습니다.")
            return []
        # { '토큰값1': true, '토큰값2': true } 와 같은 형식이므로, 키(토큰값)만 추출하여 리스트로 만듭니다.
        return list(tokens_dict.keys())
    except Exception as e:
        print(f"오류: DB에서 토큰을 읽지 못했습니다 - {e}")
        return []

def send_fcm_multicast_notification(title, body, link, tokens):
    """
    웹 푸시 방식: 여러 토큰(브라우저)에 한 번에 알림을 보냅니다. (Multicast)
    """
    if not tokens:
        # 보낼 토큰이 없으면 함수를 조용히 종료합니다.
        return

    try:
        # 여러 토큰에 보낼 때는 MulticastMessage를 사용합니다.
        message = messaging.MulticastMessage(
            # 웹 푸시에서는 notification 대신 webpush 객체를 사용하는 것이 더 세밀한 제어가 가능합니다.
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    # 알림에 표시될 아이콘 이미지 URL (선택사항)
                    # icon="https://your-website.com/icon.png" 
                ),
                # 알림 클릭 시 이동할 링크 설정
                fcm_options=messaging.WebpushFCMOptions(
                    link=link
                ),
            ),
            tokens=tokens, # DB에서 가져온 모든 토큰 리스트
        )
        response = messaging.send_multicast(message)
        print(f"-> 총 {response.success_count}개의 웹 브라우저에 알림 발송 성공.")
        if response.failure_count > 0:
            print(f"-> {response.failure_count}개의 알림 발송 실패.")
            # 실패한 토큰은 DB에서 삭제하는 로직을 추가할 수 있습니다.
            # 예: for i, resp in enumerate(response.responses): if not resp.success: print(f"실패 토큰: {tokens[i]}")
    except Exception as e:
        print(f"오류: FCM 멀티캐스트 메시지 발송 실패 - {e}")


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


# --- 메인 실행 로직 (웹 푸시에 맞게 최종 수정) ---
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
            
            # 1. DB에 저장된 모든 웹 브라우저 토큰을 가져옴
            all_tokens = get_all_tokens_from_db()

            if all_tokens:
                # 2. 모든 토큰에 웹 푸시 알림 발송
                send_fcm_multicast_notification(
                    title="새 공지사항 알림",
                    body=latest_title,
                    link=latest_link,
                    tokens=all_tokens
                )
            
            # 3. 새로 보낸 ID를 DB에 저장 (알림 성공 여부와 관계없이 ID는 저장)
            save_id_to_db(latest_post_num)
        else:
            print("-> 새로운 공지사항이 없습니다. 알림을 발송하지 않습니다.")
    
    print("\n작업을 종료합니다.")