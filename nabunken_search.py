import requests
import time
import urllib.parse
from bs4 import BeautifulSoup # HTMLからのデータ抽出
from jp_pref.prefecture import name2code # pip install jp_pref

base_url="https://sitereports.nabunken.go.jp"

def get_response(url):# ページを取得する
    session = requests.Session()  # セッションを開始
    try:
        response = session.get(url)  # GETリクエストを投げる
        if response.status_code != 200:
            print(f"エラー: ステータスコード {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"リクエスト中にエラーが発生しました: {e}")
    session.close(); time.sleep(5)  # Waitを入れておく
    return response

def get_page_num(response_text):# ページ数を取得する
    soup = BeautifulSoup(response_text, "html.parser")
    page_items = soup.select('ul.pagination li') # pagination内のli要素を取得
    # paginationがページ上下に付いているので2で割る、また、最後に飛ぶリンク分で-1    
    return 1 if len(page_items)==0 else int(len(page_items)/2-1)

def make_url(serch_options,page):#検索結果を表示するURLを作成する
    url = "/ja/search-site?has_file=x" if page==0 else f"/ja/search-site/p/{page+1}?has_file=x"
    url=base_url+url
    for key in serch_options:
        if type(serch_options[key])== list:
            for idx, item in enumerate(serch_options[key]):
                if type(serch_options[key])== list: # 複数指定するなら[]を付ける
                    url+=f"&{key}%5B%5D="+urllib.parse.quote(item)
                else: # 複数指定時も単一での指定時もitemはURLエンコードする
                    url+=f"&{key}="+urllib.parse.quote(item)   
        else:
            url+=f"&{key}="+urllib.parse.quote(serch_options[key])     
    return url

def fetch_results(response_text):# ページテキストから検索結果を取得する
    soup = BeautifulSoup(response_text,"html.parser")
    results = [] # 検索結果を格納する
    for doc in soup.select(".document_list_item"):
        # selectは、CSSセレクタ＝「クラス名指定はピリオドを前に付加する」で検索
        title = doc.select_one(".list_title").get_text(strip=True)
        url= doc.select_one(".list_title").find('a')['href']
        fields = doc.select_one(".fields").get_text(strip=True)
        results.append({"title": title, "url":url,
                        "fields": fields.replace('ほか', '').split()})
    return results

def getelevation(latlon): # 緯度経度から標高を返す　#https://maps.gsi.go.jp/development/elevation_s.html
    url="https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php?"
    url+=f"lon={latlon[1]}&lat={latlon[0]}&outtype=JSON"
    return get_response(url).json()["elevation"] # JSON返り値から標高を返す

def get_latlon(response_text):# 詳細ページのページテキストから緯度・経度を取得する
        soup = BeautifulSoup(response_text, "html.parser")
        results=[]; document_list = soup.select(".copy-clipboard-text")
        for doc in document_list:
            text=doc.get_text(strip=True)
            if set(text).issubset(set("0123456789. ")): # 緯度経度の書式なら
                latlon=text.split()
                latlon.append(getelevation(latlon)) # 標高も追加
                results.append(latlon) # [lat,lon,elevation]
        return results

def get_locations(search_options): # 
    # 検索URLを作成して最初のページにアクセスして、ページ内容と全ページ数を取得
    response_text=get_response(make_url(search_options,0)).text # ページ内容取得
    locations=[]# 検索条件に応じた検索結果を作成する。まずは最初のページから検索内容一覧を作る
    for l in fetch_results(response_text):
        locations.append(l)
    for i in range(get_page_num(response_text)-1):# 残りのページから、検索内容一覧を更新する
        locations+=fetch_results(get_response(make_url(search_options,i+1)).text)
    for loc in locations: # 詳細ページをもとに緯度経度も追加
        print(i)
        loc["latlons"]=get_latlon(get_response(base_url+loc['url']).text)
        print(loc)
    return locations

def prefs2codes(prefs): # 都道府県の名称リストをJIS X 0401-1973コードのリストに変換
    return [str(name2code(name)) for name in prefs]