from urllib.parse import urlparse
import os
import json
import requests
import threading
import time

URL = 'https://serpapi.com/search?api_key={api_key}&q={query}&start={start}&num=100&engine=google' #API URL
ERR_MESSAGE={
    'hour_limit': 'You are exceeding 1,000 searches per hour. Please contact support, or spread out your searches.',
    'no_result': 'Google hasn\'t returned any results for this query.'
}

keywords_dict = json.load(open('keyword.json', 'r', encoding='UTF-8'))
burls = keywords_dict['blacklist']['url'] #url 블랙리스트
bcontents = keywords_dict['blacklist']['content'] #내용 블랙리스트
api_key = '54a8d21c3d1d8390d493eefb6078043f1ab0cdc4adba148352feea3c2fe9128a'
fcontents = None #내용 필터링 키워드 변수
config = json.load(open('search_config.json', 'r', encoding='UTF-8')) if os.path.isfile('search_config.json') else {} #검색 index 저장

def get_search_result_by_api(query, start):
    try:
        res = requests.get(URL.format_map({
            'api_key': api_key,
            'query': query,
            'start': start
        }))    
        result = json.loads(res.text)        
        if 'error' in result:            
            return result['error']
        return result['organic_results']
    except:
        return None

#불법 서비스 검사
def is_illegal_service(url, title,  check_seq):
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
    print(search_key+':'+keyword+' starts with ', idx)

    while True:
        result_json = get_search_result_by_api(keyword, idx)
        
        #최대 요청 초과
        if result_json == ERR_MESSAGE['hour_limit']:  
            print(search_key+':'+keyword+' Expired')
            break

        if (result_json is None) or (result_json == ERR_MESSAGE['no_result']):
            idx += 100            
            continue

        for ret in result_json:
            if is_illegal_service(ret['link'], ret['title'], check_seq):
                with open('lists/'+search_key+'/'+keyword+'.txt', 'a+', encoding='UTF-8') as fp:
                    fp.write(ret['link']+' | '+ret['title']+'\n')
                    fp.close()
                print(search_key+':'+keyword+' updated')
        idx += 100            
        save_config(search_key, keyword, idx)
        time.sleep(10)

#index 저장 함수
def save_config(search_key, keyword, idx):
    global config
    config[search_key][keyword] = idx
    print(config)
    json.dump(config, open('search_config.json', 'w+', encoding='UTF-8'), ensure_ascii=False)

#검색
def search(search_key):
    global fcontents
    _keyword = keywords_dict[search_key]
    keywords = _keyword['skeyword']['content'] #검색 키워드 가져오기
    fcontents = _keyword['ckeyword']['content'] #내용 필터링 키워드 가져오기
    check_seq = _keyword['ckeyword']['check_sequence']

    if search_key not in config:
        config[search_key] = {}

    directory = 'lists/'+search_key+'/'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    
    for keyword in keywords:
        t = threading.Thread(target=th_search, args=(search_key, keyword, check_seq))  
        t.start()

if __name__ == "__main__":
    search('dobak')