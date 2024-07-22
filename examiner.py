import pickle
import hashlib

import google.generativeai as genai
from google.auth.exceptions import DefaultCredentialsError

from config import *


questions = ['''1. 根據本課程講座分享，資安新思維「永不信任，一律驗證」的概念是？
0: 零信任
1: 數位平等
2: 網路釣魚
3: 社交工程''',
'''2. 根據本課程講座分享，2023年彰化肉品市場發生什麼事件，導致停業一天損失約兩千萬？
0: 員工罷工
1: 駭客攻擊
2: 口蹄疫
3: 豬隻遭竊''',
'''3. 美國NIST(國家標準和技術研究院)對「數位韌性」的定義為何？
0: 運用數位技術打造或調整業務流程、文化和客戶體驗，以因應外在環境和市場局勢變化
1: 將所有事物、流程均以資料方式呈現，並以資料傳遞之角度重新設計 政府服務樣態
2: 使用數位資源或被數位資源賦能的系統，讓組織在面臨敵對與不利的情況時，能夠保有預判、承受、適應、復原的能力，此種能力讓組織得以於競爭激烈的數位環境中，仍然可以依靠數位資源實現組織的目標及任務
3: 在虛實整合文明空間中，發揮創新活動，持續推動數位轉型，實踐社會永續、經濟永續與環境永續，為人類開創永續未來'''
]


genai.configure(api_key=GOOGLE_API_KEY)

class E():
    model = None
    cache = dict()
    PROMPT = '請回答以下問題（提供選項數字即可，不用解釋）：'

    @staticmethod
    def load_cache():
        try:
            with open('examiner.pkl', 'rb') as fp:
                E.cache = pickle.load(fp)
        except (FileNotFoundError, pickle.PickleError, EOFError):
            ...

    @staticmethod
    def save_cache():
        with open('examiner.pkl', 'wb') as fp:
            pickle.dump(E.cache, fp)

    @staticmethod
    def init():
        try:
            E.model = genai.GenerativeModel('gemini-1.0-pro-latest')
            E.model.generate_content('Hello AI')
        except DefaultCredentialsError:
            E.model = None
        E.load_cache()

    @staticmethod
    def query(prompt: str) -> str:
        qkey = ''.join(c_ for c_ in prompt.split('\n')[0] if c_.isalnum() and not c_.isdigit())
        print(qkey)
        qkey = hashlib.md5(qkey.encode()).hexdigest()
        print(qkey)
        if qkey in E.cache:
            print(E.cache[qkey])
            return E.cache[qkey]['answer']
        if E.model is None:
            print(prompt)
            return prompt.split('\n')[-1]  # Return last answer if generative AI is not available.
        response = E.model.generate_content(E.PROMPT + '\n' + prompt)
        print(qkey, response.text)
        E.cache[qkey] = {
            'qkey': qkey,
            'question': prompt,
            'answer': response.text,
        }
        E.save_cache()
        return response.text

E.init()

if __name__ == '__main__':
    for q in questions:
        E.query(q)
