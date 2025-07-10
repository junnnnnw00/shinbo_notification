import requests
from bs4 import BeautifulSoup
import os
import time
import json
import firebase_admin
from firebase_admin import credentials, messaging, db
from urllib.parse import urljoin

# --- 설정 부분 ---
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

# --- HTML 기반 크롤링 ---
def scrape_html_announcements(region):
    try:
        response = requests.get(region["url"], timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"오류: {region['name_kr']} 사이트에 접속할 수 없습니다. ({e})")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("div.board-text table tbody tr")

    active_announcements = []
    for row in rows:
        status_cell = row.select_one("td:nth-of-type(6)")
        if status_cell and status_cell.select_one("span.state.ing"):
            status = status_cell.text.strip()
            id_cell = row.select_one("td:nth-of-type(1)")
            title_cell = row.select_one("td:nth-of-type(3) a")

            if id_cell and title_cell:
                link_href = title_cell['href']
                full_link = urljoin(region['url'], link_href)

                active_announcements.append({
                    "id": id_cell.text.strip(),
                    "title": title_cell.text.strip(),
                    "link": full_link,
                    "status": status
                })

    return active_announcements

# --- 코렉(KOREG) Ajax 크롤링 ---
def scrape_koreg_announcements(region):
    s = requests.Session()
    try:
        s.get(f"{region['set_region_url']}?cgfcd={region['cgfcd']}", allow_redirects=False)
    except Exception as e:
        print(f"오류: {region['name_kr']} 지역 설정 실패 - {e}")
        return []

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }

    data = {
        "goodScptCd": "",
        "goods_chrt_cd_list": "",
        "untct_fbank_list": "",
        "grt_sprt_lmt_amt": "",
        "startDate": "",
        "endDate": "",
        "keyWord": "",
    }

    try:
        res = s.post(region['ajax_url'], headers=headers, data=data, timeout=15)
        res.raise_for_status()
        json_data = res.json()
    except Exception as e:
        print(f"오류: {region['name_kr']} Ajax 요청 실패 - {e}")
        return []

    announcements = []
    for item in json_data.get("resultList", []):
        if item.get("goodsSttsNm") == "시행중":
            announcements.append({
                "id": item.get("goodsSn", ""),
                "title": item.get("goodsNm", "").strip(),
                "link": f"https://untact.koreg.or.kr/grtApp/selectGrtGoodsDetail.do?goodsSn={item.get('goodsSn')}",
                "status": item.get("goodsSttsNm", "")
            })

    return announcements

# --- DB 및 알림 ---
def get_data_from_db(path):
    try:
        return db.reference(path).get()
    except Exception:
        return None

def set_data_to_db(path, data):
    try:
        db.reference(path).set(data)
        print(f"-> DB 경로 '{path}'에 새로운 데이터 저장 성공")
    except Exception as e:
        print(f"오류: DB 경로 '{path}'에 데이터를 저장하지 못했습니다 - {e}")

def send_fcm_notification(title, body, link, tokens):
    if not tokens:
        return
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

# --- 메인 로직 ---
if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 전체 지역 지원사업 공고 확인을 시작합니다...")
    if not initialize_fcm():
        exit()

    all_tokens = get_data_from_db('tokens')
    tokens_list = list(all_tokens.keys()) if all_tokens else []

    for region in REGIONS_CONFIG:
        region_id, region_name_kr = region["id"], region["name_kr"]
        db_path = f'announcements/{region_id}'
        print(f"\n--- {region_name_kr} 작업 시작 ---")

        if region["type"] == "html":
            scraped_data = scrape_html_announcements(region)
        elif region["type"] == "koreg":
            scraped_data = scrape_koreg_announcements(region)
        else:
            print(f"오류: 알 수 없는 타입 '{region['type']}'")
            continue

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
