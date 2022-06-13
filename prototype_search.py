from urllib.parse import urlparse
import os
import json
import requests
import threading
import time

URL = 'http://172.30.1.200:8080/api/search/{query}?start={start}&count=10' #API URL
DELAY_SEC = 60*60*2 #2 HOURS
ERROR_MSG = {
    'bot_text': 'Google detected our system as bot',
    'unexpected': 'Unexpected error occured'
}

keywords_dict = json.load(open('keyword.json', 'r', encoding='UTF-8'))
burls = keywords_dict['blacklist']['url'] #url 블랙리스트
bcontents = keywords_dict['blacklist']['content'] #내용 블랙리스트
fcontents = None #내용 필터링 키워드 변수
config = json.load(open('proto_search_config.json', 'r+', encoding='UTF-8')) \
    if os.path.isfile('proto_search_config.json') \
    else {} #검색 index 저장

def get_search_result_by_api(query, start):
    try:
        res = requests.get(URL.format_map({            
            'query': query,
            'start': start
        }))    
        result = json.loads(res.text)        
        if 'error' in result:
            return result['error']
        return result['result']
    except Exception as e:
        print(e)
        return None

#불법 서비스 검사
def is_illegal_service(url, title, check_seq):
    global burls, bcontents, fcontents

    #url 블랙리스트 검사
    for burl in burls:
        _url = urlparse(url).netloc
        if burl in _url:
            return False
    
    #url 내용 가져오기    
    try:
        content = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.57 Whale/3.14.133.23 Safari/537.36'
        }).text
    except: #내용 가져오기 실패 시
        return False

    #내용 블랙리스트 검사
    for bcontent in bcontents:
        if (bcontent in content) or (bcontent in title):
            return False
    
    #나오는 단어 개수 검사
    cnt = {}

    for fcontent in fcontents:
        cnt[fcontent] = content.count(fcontent) > 0
    
    _seq = 0
    for check in cnt.values():
        if check:
            _seq += 1
    
    return _seq >= check_seq

def th_search(search_key, keyword, check_seq):
    global config    
    idx = config[search_key][keyword] if search_key in config and keyword in config[search_key] else 0
    while True:
        result_json = get_search_result_by_api(keyword, idx)

        if result_json is None:
            idx += 10
            continue

        if result_json == ERROR_MSG['unexpected']:
            continue

        #봇으로 인식
        if result_json == ERROR_MSG['bot_text']:
            print('Google detected lcoal api as bot.\n%s:%s Thread waits for %.1f hours.\n' % (search_key, keyword, DELAY_SEC/3600))
            time.sleep(DELAY_SEC)
            continue

        for ret in result_json:
            try:            
                if is_illegal_service(ret['url'], ret['title'], check_seq):
                    with open('proto/lists/'+search_key+'/'+keyword+'.txt', 'a+', encoding='UTF-8') as fp:
                        fp.write(ret['url']+' | '+ret['title']+'\n')
                        fp.close()
                    print(search_key+':'+keyword+' updated')
            except:
                print(ret)

        idx += 10
        save_config(search_key, keyword, idx)
        time.sleep(10)

#index 저장 함수
def save_config(search_key, keyword, idx):
    global config
    config[search_key][keyword] = idx
    print(config)
    json.dump(
        config, 
        open('proto_search_config.json', 'w+', encoding='UTF-8'),
        ensure_ascii=False
    )

#검색
def search(search_key):
    global fcontents
    _keyword = keywords_dict[search_key]
    keywords = _keyword['skeyword']['content'] #검색 키워드 가져오기
    fcontents = _keyword['ckeyword']['content'] #내용 필터링 키워드 가져오기
    check_seq = _keyword['ckeyword']['check_sequence']

    if search_key not in config:
        config[search_key] = {}

    directory = 'proto/lists/'+search_key+'/'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    
    for keyword in keywords:
        t = threading.Thread(target=th_search, args=(search_key, keyword, check_seq))            
        t.start()

if __name__ == "__main__":
    search('dobak')