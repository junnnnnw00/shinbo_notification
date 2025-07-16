import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# ==================== 공통 유틸 ==================== #
def log(msg: str) -> None:
    """터지지 말라고 바로바로 찍어주는 로그"""
    print(msg, flush=True)

MAX_RETRY   = 3   # AJAX 재시도 횟수
RETRY_DELAY = 3   # 재시도 간격(sec)

# ==================== 설정 ==================== #
REGIONS_CONFIG = [
    {
        "id": "koreg_kws",
        "name_kr": "보증드림-강원신용보증재단",
        "type": "koreg",
        "cgfcd": "KWS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    # ... 나머지 지역 그대로 ...
]

DATABASE_URL = 'https://shinbo-notify-default-rtdb.asia-southeast1.firebasedatabase.app/'

# ==================== Firebase ==================== #
def initialize_fcm():
    try:
        if not firebase_admin._apps:
            log("Firebase Admin SDK 초기화")
            cred_json = json.loads(os.environ["FIREBASE_CREDENTIALS_JSON"])
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        return True
    except Exception as e:
        log(f"Firebase 초기화 실패 - {e}")
        return False

# ==================== KOREG 스크래핑 ==================== #
def scrape_koreg_announcements(region):
    """정상 리스트 얻으면 list[dict], 실패면 None"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    main_page_url = "https://untact.koreg.or.kr/web/lay1/program/S1T1C5/grtApp/selectGrtGoodsList.do"
    csrf_header_name = "X-CSRF-TOKEN"

    for attempt in range(1, MAX_RETRY + 1):
        try:
            # 1) 지역 세팅
            s.get(f"{region['set_region_url']}?cgfcd={region['cgfcd']}", timeout=30)

            # 2) 메인 페이지에서 CSRF 토큰 캐기
            main_res = s.get(main_page_url, timeout=30)
            main_res.raise_for_status()
            soup = BeautifulSoup(main_res.text, 'html.parser')
            token_tag = soup.select_one('input[name="_csrf"]')
            if not token_tag:
                raise ValueError("CSRF 토큰 없음")
            csrf_token = token_tag['value']

            # 3) AJAX POST
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": main_page_url,
                csrf_header_name: csrf_token
            }
            data = {
                "goodScptCd": "", "goods_chrt_cd_list": "", "untct_fbank_list": "",
                "grt_sprt_lmt_amt": "", "startDate": "", "endDate": "", "keyWord": "",
                "_csrf": csrf_token
            }
            res = s.post(region['ajax_url'], headers=headers, data=data, timeout=30)
            res.raise_for_status()
            json_data = res.json()

            # 4) 결과 검증
            items = json_data.get("list", [])
            if not items:
                raise ValueError("list 비어있음")

            # 5) 파싱
            return [
                {
                    "id": str(item.get("grt_goods_no", "")),
                    "title": item.get("goods_nm", "").strip(),
                    "link": f"https://untact.koreg.or.kr/web/lay1/program/S1T5C341/grtApp/selectGrtGoodsDtlView.do?grt_goods_no={item.get('grt_goods_no')}",
                    "status": "공고중"
                }
                for item in items
            ]

        except Exception as e:
            log(f"{region['name_kr']} 스크랩 실패 {attempt}/{MAX_RETRY} - {e}")
            if attempt < MAX_RETRY:
                time.sleep(RETRY_DELAY)

    # 전부 실패
    return None

def scrape_html_announcements(region):  # 미사용
    return None

# ==================== DB & FCM ==================== #
def get_data_from_db(path):
    try:
        return db.reference(path).get()
    except Exception:
        return None

def set_data_to_db(path, data):
    try:
        db.reference(path).set(data)
        log(f"DB '{path}' 저장 OK")
    except Exception as e:
        log(f"DB 저장 실패 - {e}")

def send_fcm_notification(title, body, link, tokens):
    if not tokens:
        return
    ok, fail = 0, 0
    for t in tokens:
        try:
            messaging.send(messaging.Message(data={"title": title, "body": body, "link": link}, token=t))
            ok += 1
        except Exception as e:
            log(f"토큰 {t[:20]}... 실패 - {e}")
            fail += 1
    log(f"알림 결과: 성공 {ok}, 실패 {fail}")

# ==================== 메인 ==================== #
def main():
    log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 지역 공고 체크 시작")
    if not initialize_fcm():
        return

    tokens = get_data_from_db('tokens') or {}
    tokens_list = list(tokens.keys())

    for region in REGIONS_CONFIG:
        name = region["name_kr"]
        db_path = f"announcements/{name}"
        log(f"\n--- {name} ---")

        # 스크래핑
        scraped = None
        if region["type"] == "koreg":
            scraped = scrape_koreg_announcements(region)
        else:
            scraped = scrape_html_announcements(region)

        if scraped is None:
            log("비정상 응답이라 DB 건드리지 않음")
            continue
        if not scraped:
            log("빈 리스트. 기존 데이터 유지")
            continue

        # 정상 리스트 얻었음
        old = get_data_from_db(db_path) or []
        new_ids = {i['id'] for i in scraped} - {i['id'] for i in old}

        if new_ids:
            log(f"새 공고 {len(new_ids)}건 발견, 알림 쏜다")
            for nid in new_ids:
                item = next(i for i in scraped if i['id'] == nid)
                send_fcm_notification(f"[{name}] 신규 공고", item['title'], item['link'], tokens_list)
        else:
            log("새 공고 없음")

        # DB 갱신
        set_data_to_db(db_path, scraped)

    log("\n--- 끝 ---")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"치명적 오류 - {e}")
