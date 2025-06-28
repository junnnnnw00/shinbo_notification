import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging

# --- 설정 부분 ---
NOTICE_URL = "https://www.ulsanshinbo.co.kr/04_notice/?mcode=0404010000"
LAST_POST_FILE = "latest_post.txt" # GitHub Actions 환경에서는 이 파일을 사용하지 않음
BASE_URL = "https://www.ulsanshinbo.co.kr"

# FCM 알림을 보낼 주제(Topic) 이름. 앱에서도 이 이름으로 구독해야 함.
FCM_TOPIC = "new_notice" 

def initialize_fcm():
    """FCM 초기화 함수. GitHub Actions의 Secrets를 사용합니다."""
    try:
        # GitHub Actions Secret에서 받아온 JSON 문자열을 파싱
        firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        if not firebase_credentials_json:
            print("오류: FIREBASE_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다.")
            return False

        cred_json = json.loads(firebase_credentials_json)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        print(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False
    
def send_fcm_notification(title, body, link):
    """FCM으로 모든 구독자에게 푸시 알림을 보냅니다."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            # data 페이로드: 앱이 알림을 받았을 때 추가 정보를 사용할 수 있게 함 (예: 링크)
            data={
                'link': link,
            },
            topic=FCM_TOPIC,
        )

        response = messaging.send(message)
        print(f"-> FCM 메시지 발송 성공: {response}")
    except Exception as e:
        print(f"오류: FCM 메시지 발송 실패 - {e}")

def get_latest_post_info():
    """
    웹사이트에 접속하여 최신 공지사항 정보를 가져옵니다.
    class="ntc"를 가진 고정 공지는 건너뛰고 가장 위에 있는 일반 게시물을 반환합니다.
    
    Returns:
        tuple: (게시물 번호, 제목, 링크) 형태의 튜플. 최신 글이 없으면 (None, None, None) 반환.
    """
    try:
        response = requests.get(NOTICE_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: 웹사이트에 접속할 수 없습니다. ({e})")
        return None, None, None

    soup = BeautifulSoup(response.text, "html.parser")

    # 게시판 테이블의 모든 행(tr)을 선택
    # <tbody> 태그 바로 아래에 있는 <tr> 들을 대상으로 함
    rows = soup.select("div.board-text table tbody tr")

    # 고정 공지를 제외한 첫 번째 일반 게시물을 찾기 위해 반복
    for row in rows:
        # <tr> 태그에 'ntc' 클래스가 있으면 고정 공지이므로 건너뜀
        if 'ntc' in row.get('class', []):
            continue

        # 'ntc' 클래스가 없는 첫 번째 게시물이 우리가 찾는 최신 글
        # 게시물 번호 추출
        post_number_td = row.select_one("td.num")
        if not post_number_td:
            continue
        
        post_number = post_number_td.text.strip()

        # 제목과 링크 추출
        subject_td_link = row.select_one("td.link a")
        if subject_td_link:
            title = subject_td_link.text.strip()
            relative_link = subject_td_link['href']
            full_link = BASE_URL + relative_link
            
            # 숫자 형태의 게시물 번호, 제목, 전체 링크를 반환하고 함수 종료
            return post_number, title, full_link
            
    # 일반 게시물이 하나도 없는 경우
    return None, None, None

def get_last_checked_post():
    """
    파일에 저장된 마지막 게시물 번호를 읽어옵니다.
    파일이 없으면 None을 반환합니다.
    """
    if not os.path.exists(LAST_POST_FILE):
        return None
    try:
        with open(LAST_POST_FILE, 'r') as f:
            return f.read().strip()
    except IOError as e:
        print(f"오류: 파일을 읽을 수 없습니다. ({e})")
        return None

def save_last_checked_post(post_number):
    """
    새로운 최신 게시물 번호를 파일에 저장합니다.
    """
    try:
        with open(LAST_POST_FILE, 'w') as f:
            f.write(str(post_number))
    except IOError as e:
        print(f"오류: 파일에 저장할 수 없습니다. ({e})")

# --- 메인 실행 로직 ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 신규 공지사항 확인 및 FCM 발송 작업을 시작합니다...")

    if not initialize_fcm():
        exit() # FCM 초기화 실패 시 작업 중단

    latest_post_num, latest_title, latest_link = get_latest_post_info()

    if not latest_post_num:
        print("-> 최신 게시물 정보를 가져오는 데 실패했습니다.")
    else:
        # 여기서는 매번 최신 글 1개를 가져와서 알림을 보내는 대신,
        # 마지막으로 보낸 글과 비교하는 로직이 필요합니다.
        # 간단한 구현을 위해, 여기서는 항상 최신 글 1개를 가져와서
        # "이런 글이 최신글이다" 라고 알림을 보내는 방식으로 단순화 할 수 있습니다.
        # (더 좋은 방법은 Firebase DB에 마지막 게시물 번호를 저장하고 비교하는 것입니다.)
        
        print("\n★★★ 최신 공지사항 정보 ★★★")
        print(f"  - 번호: {latest_post_num}")
        print(f"  - 제목: {latest_title}")
        print(f"  - 링크: {latest_link}")
        
        # FCM 알림 발송
        send_fcm_notification(
            title="새 공지사항 알림", 
            body=latest_title, 
            link=latest_link
        )
    
    print("\n작업을 종료합니다.")