import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db
from urllib.parse import urljoin

# --- ★★★ 디버깅을 위한 강제 출력 로그 함수 ★★★ ---
def log(msg: str) -> None:
    """실행 즉시 로그를 출력하는 함수"""
    print(msg, flush=True)

# --- 설정 부분 (사용자 코드 유지) ---
REGIONS_CONFIG = [
    # {
    #     "id": "ulsan",
    #     "name_kr": "울산신용보증재단",
    #     "type": "html",
    #     "url": "https://www.ulsanshinbo.co.kr/02_sinbo/?mcode=0402060000",
    #     "base_url": "https://www.ulsanshinbo.co.kr"
    # },
    {
        "id": "koreg_kws",
        "name_kr": "보증드림-강원신용보증재단",
        "type": "koreg",
        "cgfcd": "KWS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    # ... (다른 koreg 지역 설정은 그대로 유지) ...
    {
        "id": "koreg_cbs",
        "name_kr": "보증드림-충북신용보증재단",
        "type": "koreg",
        "cgfcd": "CBS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
]

DATABASE_URL = 'https://shinbo-notify-default-rtdb.asia-southeast1.firebasedatabase.app/'

def initialize_fcm():
    try:
        if not firebase_admin._apps:
            log("Firebase Admin SDK 초기화를 시작합니다...")
            firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
            if not firebase_credentials_json:
                raise ValueError("FIREBASE_CREDENTIALS_JSON 환경 변수가 설정되지 않았습니다.")
            cred_json = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        log("-> Firebase Admin SDK 초기화 성공")
        return True
    except Exception as e:
        log(f"오류: Firebase Admin SDK 초기화 실패 - {e}")
        return False

# --- HTML 기반 크롤링 ---
def scrape_html_announcements(region):
    log(f"HTML 스크래핑 시작: {region['name_kr']}")
    # ... (이전 코드와 동일)
    return [] # 현재는 사용하지 않으므로 빈 리스트 반환

# --- 코렉(KOREG) Ajax 크롤링 ---
def scrape_koreg_announcements(region):
    s = requests.Session()
    try:
        log(f"KOREG 지역 설정 시도: {region['name_kr']}")
        s.get(f"{region['set_region_url']}?cgfcd={region['cgfcd']}", allow_redirects=True, timeout=20)
        log("-> KOREG 지역 설정 완료")
    except Exception as e:
        log(f"오류: {region['name_kr']} 지역 설정 실패 - {e}")
        return []

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }
    data = {"goodScptCd": "", "goods_chrt_cd_list": "", "untct_fbank_list": "", "grt_sprt_lmt_amt": "", "startDate": "", "endDate": "", "keyWord": ""}

    try:
        log(f"KOREG 데이터 Ajax 요청 시도: {region['name_kr']}")
        res = s.post(region['ajax_url'], headers=headers, data=data, timeout=20)
        res.raise_for_status()
        log("-> KOREG 데이터 Ajax 요청 성공")
        
        if "application/json" not in res.headers.get("Content-Type", ""):
            raise ValueError(f"응답이 JSON이 아닙니다. 응답 내용: {res.text[:200]}")
        
        json_data = res.json()
    except Exception as e:
        log(f"오류: {region['name_kr']} Ajax 요청 실패 - {e}")
        return []

    announcements = []
    for item in json_data.get("resultList", []):
        if item.get("goodsSttsNm") == "시행중":
            announcements.append({
                "id": str(item.get("goodsSn", "")),
                "title": item.get("goodsNm", "").strip(),
                "link": f"https://untact.koreg.or.kr/grtApp/selectGrtGoodsDetail.do?goodsSn={item.get('goodsSn')}",
                "status": item.get("goodsSttsNm", "")
            })
    return announcements

# --- DB 및 알림 ---
def get_data_from_db(path):
    try:
        return db.reference(path).get()
    except Exception: return None

def set_data_to_db(path, data):
    try:
        db.reference(path).set(data)
        log(f"-> DB 경로 '{path}'에 새로운 데이터 저장 성공")
    except Exception as e:
        log(f"오류: DB 경로 '{path}'에 데이터를 저장하지 못했습니다 - {e}")

def send_fcm_notification(title, body, link, tokens):
    # ... (이전 코드와 동일)
    pass

# --- 메인 로직 ---
def main():
    log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 전체 지역 지원사업 공고 확인을 시작합니다...")
    if not initialize_fcm():
        log("초기화 실패로 작업을 중단합니다.")
        return

    log("DB에서 토큰 정보를 가져옵니다...")
    all_tokens = get_data_from_db('tokens')
    tokens_list = list(all_tokens.keys()) if all_tokens else []
    log(f"-> {len(tokens_list)}개의 토큰 확인")

    for region in REGIONS_CONFIG:
        region_id, region_name_kr = region["id"], region["name_kr"]
        db_path = f'announcements/{region_id}'
        log(f"\n--- {region_name_kr} 작업 시작 ---")

        scraped_data = []
        if region["type"] == "html":
            scraped_data = scrape_html_announcements(region)
        elif region["type"] == "koreg":
            scraped_data = scrape_koreg_announcements(region)
        else:
            log(f"오류: 알 수 없는 타입 '{region['type']}'")
            continue

        log(f"-> 스크래핑 완료: 총 {len(scraped_data)}개의 '시행중' 공고 발견")

        db_data = get_data_from_db(db_path) or []
        scraped_ids = {item['id'] for item in scraped_data}
        db_ids = {item['id'] for item in db_data}
        new_item_ids = scraped_ids - db_ids

        if new_item_ids:
            log(f"-> ★★★ {len(new_item_ids)}개의 새로운 공고 발견! 알림 발송 ★★★")
            # ... (알림 발송 로직은 생략 가능, 스크래핑 확인이 우선)
        else:
            log("-> 새로운 공고가 없습니다.")

        set_data_to_db(db_path, scraped_data)

    log("\n--- 모든 작업 종료 ---")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 최후의 보루: 스크립트 전체에서 예상치 못한 오류 발생 시 로그 남기기
        log(f"!!!!!!!! 스크립트 최상위에서 심각한 오류 발생: {e} !!!!!!!!")
