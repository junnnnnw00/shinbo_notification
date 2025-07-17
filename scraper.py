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
        "id": "koreg_jcg",
        "name_kr": "보증드림-제주신용보증재단",
        "type": "koreg",
        "cgfcd": "JCG",
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

MAX_SCRAPE_ATTEMPTS = 5      # 한 사이클에 GET 5번
RETRY_DELAY         = 2      # 실패했을 때 텀

def scrape_koreg_announcements(region):
    """
    성공한 시도 중 '가장 많은 공고'를 리턴.
    - 리스트가 하나도 안 나오면 None
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    main_page_url = "https://untact.koreg.or.kr/web/lay1/program/S1T1C5/grtApp/selectGrtGoodsList.do"
    csrf_header_name = "X-CSRF-TOKEN"

    best_items = []
    for attempt in range(1, MAX_SCRAPE_ATTEMPTS + 1):
        try:
            # 1) 지역 세팅
            s.get(f"{region['set_region_url']}?cgfcd={region['cgfcd']}", timeout=30)

            # 2) CSRF 토큰
            soup = BeautifulSoup(s.get(main_page_url, timeout=30).text, 'html.parser')
            token_tag = soup.select_one('input[name="_csrf"]')
            if not token_tag:
                raise ValueError("CSRF 토큰 못 찾음")
            csrf_token = token_tag['value']

            # 3) GET AJAX (params 사용)
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": main_page_url,
                csrf_header_name: csrf_token
            }
            params = {
                "goodScptCd": "", "goods_chrt_cd_list": "", "untct_fbank_list": "",
                "grt_sprt_lmt_amt": "", "startDate": "", "endDate": "", "keyWord": "",
                "_csrf": csrf_token
            }
            res = s.get(region['ajax_url'], headers=headers, params=params, timeout=30)
            res.raise_for_status()
            data = res.json()
            items = data.get("list", [])

            log(f"{region['name_kr']} 시도 {attempt}: {len(items)}건")

            if len(items) > len(best_items):
                best_items = items

        except Exception as e:
            log(f"{region['name_kr']} 시도 {attempt} 실패 - {e}")
            time.sleep(RETRY_DELAY)

    # 최종 검증
    if not best_items:
        return None

    # 파싱 & 중복 제거
    seen = set()
    parsed = []
    for item in best_items:
        gid = str(item.get("grt_goods_no", ""))
        if gid in seen:
            continue
        seen.add(gid)
        parsed.append({
            "id": gid,
            "title": item.get("goods_nm", "").strip(),
            "link": f"https://untact.koreg.or.kr/web/lay1/program/S1T5C341/grtApp/selectGrtGoodsDtlView.do?grt_goods_no={gid}",
            "status": "공고중"
        })
    return parsed

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
