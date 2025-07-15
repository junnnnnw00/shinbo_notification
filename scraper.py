import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- 디버깅을 위한 강제 출력 로그 함수 ---
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
    {
        "id": "koreg_gns",
        "name_kr": "보증드림-경남신용보증재단",
        "type": "koreg",
        "cgfcd": "GNS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_wuf",
        "name_kr": "보증드림-경북신용보증재단",
        "type": "koreg",
        "cgfcd": "WUF",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_ttu",
        "name_kr": "보증드림-광주신용보증재단",
        "type": "koreg",
        "cgfcd": "TTU",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_ttg",
        "name_kr": "보증드림-대구신용보증재단",
        "type": "koreg",
        "cgfcd": "TTG",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_ttv",
        "name_kr": "보증드림-대전신용보증재단",
        "type": "koreg",
        "cgfcd": "TTV",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_bss",
        "name_kr": "보증드림-부산신용보증재단",
        "type": "koreg",
        "cgfcd": "BSS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_sjs",
        "name_kr": "보증드림-세종신용보증재단",
        "type": "koreg",
        "cgfcd": "SJS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_uss",
        "name_kr": "보증드림-울산신용보증재단",
        "type": "koreg",
        "cgfcd": "USS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_ttt",
        "name_kr": "보증드림-인천신용보증재단",
        "type": "koreg",
        "cgfcd": "TTT",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_wug",
        "name_kr": "보증드림-전남신용보증재단",
        "type": "koreg",
        "cgfcd": "WUG",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_jbs",
        "name_kr": "보증드림-전북신용보증재단",
        "type": "koreg",
        "cgfcd": "JBS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_jcs",
        "name_kr": "보증드림-제주신용보증재단",
        "type": "koreg",
        "cgfcd": "JCS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
    {
        "id": "koreg_cns",
        "name_kr": "보증드림-충남신용보증재단",
        "type": "koreg",
        "cgfcd": "CNS",
        "ajax_url": "https://untact.koreg.or.kr/grtApp/selectGrtGoodsListAjax.do",
        "set_region_url": "https://untact.koreg.or.kr/web/inc/change_cfgcd.do"
    },
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

# --- 코렉(KOREG) Ajax 크롤링 (CSRF 토큰 적용) ---
def scrape_koreg_announcements(region):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    })
    main_page_url = "https://untact.koreg.or.kr/web/lay1/program/S1T1C5/grtApp/selectGrtGoodsList.do"
    csrf_token = None
    csrf_header_name = "X-CSRF-TOKEN" # 대부분의 경우 이 헤더 이름을 사용

    try:
        # 1. 지역 설정
        log(f"KOREG 지역 설정 시도: {region['name_kr']}")
        s.get(f"{region['set_region_url']}?cgfcd={region['cgfcd']}", timeout=30)
        log("-> KOREG 지역 설정 완료")
        
        # 2. 메인 페이지 방문하여 CSRF 토큰 획득
        log(f"KOREG 메인 페이지 방문 시도: {region['name_kr']}")
        main_res = s.get(main_page_url, timeout=30)
        main_res.raise_for_status()
        soup = BeautifulSoup(main_res.text, 'html.parser')
        
        # ★★★ 수정: meta 태그 대신 숨겨진 input 태그에서 CSRF 토큰을 찾습니다. ★★★
        csrf_token_tag = soup.select_one('input[name="_csrf"]')
        
        if not csrf_token_tag:
            raise ValueError("CSRF 토큰을 찾을 수 없습니다.")
            
        csrf_token = csrf_token_tag['value']
        log(f"-> CSRF 토큰 획득 성공: {csrf_token[:10]}...")

        # 3. CSRF 토큰을 포함하여 Ajax 요청
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": main_page_url,
            csrf_header_name: csrf_token # 획득한 CSRF 토큰을 헤더에 추가
        }
        data = {
            "goodScptCd": "", "goods_chrt_cd_list": "", "untct_fbank_list": "", 
            "grt_sprt_lmt_amt": "", "startDate": "", "endDate": "", "keyWord": "",
            "_csrf": csrf_token # 데이터 본문에도 CSRF 토큰 추가
        }

        log(f"KOREG 데이터 Ajax 요청 시도: {region['name_kr']}")
        res = s.get(region['ajax_url'], headers=headers, data=data, timeout=30)
        res.raise_for_status()
        log("-> KOREG 데이터 Ajax 요청 성공")
        
        json_data = res.json()
    except Exception as e:
        log(f"오류: {region['name_kr']} 스크래핑 과정 실패 - {e}")
        return []

    log(json_data)  # 디버깅용 로그 출력
    announcements = []
    for item in json_data.get("list", []):
        announcements.append({
            "id": str(item.get("grt_goods_no", "")),
            "title": item.get("goods_nm", "").strip(),
            "link": f"https://untact.koreg.or.kr/grtApp/selectGrtGoodsDetail.do?goodsSn={item.get('grt_goods_no')}",
            "status": "공고중"
        })
    return announcements

# --- 사용하지 않는 함수 ---
def scrape_html_announcements(region):
    return []

# --- DB 및 알림 (이전과 동일) ---
def get_data_from_db(path):
    try: return db.reference(path).get()
    except Exception: return None

def set_data_to_db(path, data):
    try:
        db.reference(path).set(data)
        log(f"-> DB 경로 '{path}'에 새로운 데이터 저장 성공")
    except Exception as e:
        log(f"오류: DB 경로 '{path}'에 데이터를 저장하지 못했습니다 - {e}")

def send_fcm_notification(title, body, link, tokens):
    if not tokens: return
    success_count, failure_count = 0, 0
    for token in tokens:
        try:
            message = messaging.Message(data={"title": title, "body": body, "link": link}, token=token)
            messaging.send(message)
            success_count += 1
        except Exception as e:
            log(f"오류: 토큰 [{token[:20]}...] 발송 실패 - {e}")
            failure_count += 1
    log(f"-> 알림 발송 결과: 성공 {success_count}건, 실패 {failure_count}건")

# --- 메인 로직 (이전과 동일) ---
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

        log(f"-> 스크래핑 완료: 총 {len(scraped_data)}개의 공고 발견")

        db_data = get_data_from_db(db_path) or []
        scraped_ids = {item['id'] for item in scraped_data}
        db_ids = {item['id'] for item in db_data}
        new_item_ids = scraped_ids - db_ids

        if new_item_ids:
            log(f"-> ★★★ {len(new_item_ids)}개의 새로운 공고 발견! 알림 발송 ★★★")
            if tokens_list:
                for new_id in new_item_ids:
                    new_item = next((item for item in scraped_data if item["id"] == new_id), None)
                    if new_item:
                        send_fcm_notification(f"[{region_name_kr}] 신규 공고", new_item['title'], new_item['link'], tokens_list)
            else:
                log("-> 알림을 보낼 사용자가 없습니다.")
        else:
            log("-> 새로운 공고가 없습니다.")

        set_data_to_db(db_path, scraped_data)

    log("\n--- 모든 작업 종료 ---")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"!!!!!!!! 스크립트 최상위에서 심각한 오류 발생: {e} !!!!!!!!")
