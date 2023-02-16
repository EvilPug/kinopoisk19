import os
import re
import time
import redis
import pickle
from selenium import webdriver
from multiprocessing.dummy import Pool
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.wait import WebDriverWait

import config as c


class GameSolver:

    def __init__(self, cook_str: str):

        webdriver.DesiredCapabilities.CHROME['acceptSslCerts'] = True

        self.driver = webdriver.Chrome(options=c.opts,
                                       service=Service(ChromeDriverManager().install()))
        self.driver.maximize_window()
        self.driver.get(c.kp_url)

        cookies = pickle.load(open(cook_str, "rb"))
        for cookie in cookies:
            self.driver.add_cookie(cookie)

        supported_games = '1234'
        self.g_db = dict()
        for i in supported_games:
            self.g_db[i] = redis.StrictRedis(host=c.host, port=c.port, db=int(i)-1,
                                             password=c.pw, charset="utf-8", decode_responses=True)

        print('Connection OK' if self.g_db['1'].get("Bahamas") == 'Nassau' else 'Error')

    def current_game(self) -> str:
        current_game = self.g_db['1'].get('game')
        return current_game

    def start_game(self, free_play: bool):

        game = self.current_game()
        self.driver.get(c.kp_url)

        xpath_expr = "//button[contains(text(),'Играть') or contains(text(),'Новый эпизод')]"
        elements = WebDriverWait(self.driver, timeout=5).until(lambda d: d.find_elements(By.XPATH, xpath_expr))
        print(f'Найдено {len(elements)} карточек с заданиями', )
        time.sleep(0.5)

        if free_play:
            time.sleep(10000)

        game_button = elements[int(game)-1]
        self.driver.execute_script("arguments[0].click();", game_button)
        xpath_expr = "//button[contains(text(),'Начать игру')]"
        start_button = WebDriverWait(self.driver, timeout=5).until(lambda d: d.find_element(By.XPATH, xpath_expr))
        self.driver.execute_script("arguments[0].click();", start_button)

        previous = self.g_db['1'].get('game')
        while True:
            game = self.g_db['1'].get('game')
            if game == previous:
                try:
                    self.play(game)
                except Exception as e:
                    print(e)
                    time.sleep(10000)
                previous = game
            else:
                break

    def get_answer_options(self) -> dict:
        answers_dict = dict()
        xpath_expr = "//span[contains(@class,'text-fit')]"
        answers = WebDriverWait(self.driver, timeout=5, poll_frequency=0.2).until(lambda d: d.find_elements(By.XPATH,
                                                                                                            xpath_expr))
        for ans in answers:
            answers_dict[ans.text.strip()] = ans
        return answers_dict

    def find_end_modal(self) -> tuple:
        time.sleep(1)
        xpath_expr = "//div[contains(text(),'Это ') or contains(text(),'Правильный ответ')]"
        fail_text = WebDriverWait(self.driver, timeout=5, poll_frequency=0.5).until(
            lambda d: d.find_element(By.XPATH, xpath_expr))
        answer = re.search("«(.*)»", fail_text.text).group(1)
        print('Правильный ответ:', answer)

        xpath_expr = "//button[contains(text(),'Продолжить игру') or contains(text(),'Играть ещё раз') " \
                     "or contains(text(),'Выбрать вселенную')] "
        resume_button = WebDriverWait(self.driver, timeout=5, poll_frequency=0.5).until(
            lambda d: d.find_element(By.XPATH, xpath_expr))
        return answer, resume_button

    def answer_is_success(self) -> bool:
        time.sleep(0.5)
        xpath_expr = "//div[contains(@class,'game__test-answers-item_state_success') or contains(@class," \
                     "'game__test-answers-item_state_error')]"
        elem = WebDriverWait(self.driver, timeout=2).until(lambda d: d.find_element(By.XPATH, xpath_expr))
        elem_class = elem.get_attribute("class").split(' ')[1]

        if elem_class == 'game__test-answers-item_state_success':
            return True
        elif elem_class == 'game__test-answers-item_state_error':
            return False
        else:
            print('Не найдено состояние кнопки ответа (правильно или неправильно)')
            raise Exception

    def play(self, game: str) -> None:
        time.sleep(1)
        r = self.g_db[game]

        if game in ['1', '4']:
            xpath_expr = "//img[contains(@class,'game__test-image-img')]"
        elif game in ['2', '3']:
            xpath_expr = "//div[contains(@class, 'game__test-question')]"
        else:
            raise Exception

        task = WebDriverWait(self.driver, timeout=5).until(lambda d: d.find_element(By.XPATH, xpath_expr))

        if game in ['1', '4']:
            task_key = task.get_attribute("src")
        elif game in ['2', '3']:
            task_key = task.text
        else:
            return None

        answer = r.get(task_key).strip() if r.get(task_key) is not None else None
        answers_dict = self.get_answer_options()
        time.sleep(1)

        if answer:
            if answer in answers_dict.keys():
                print('Фильм найден в базе. Ответ:', answer)
                self.driver.execute_script("arguments[0].click();", answers_dict[answer])
                is_success = self.answer_is_success()

                # Проверка на случай Kill la Kill (показывает неправильный ответ, хотя он правильный)
                if not is_success:
                    answer, resume_button = self.find_end_modal()
                    self.driver.execute_script("arguments[0].click();", resume_button)
                time.sleep(0.5)

            else:
                print('Несоответствие ответов из базы и на экране')

        else:
            # Нажимаем на кнопку первого ответа
            first_ans = list(answers_dict.items())[0]
            print('Фильм не найден')
            self.driver.execute_script("arguments[0].click();", first_ans[1])
            print('Нажимаем на первый ответ:', first_ans[0])
            is_success = self.answer_is_success()

            if is_success:
                answer: str = first_ans[0]
                r.mset({task_key: answer})
                print('Первый ответ правильный!')
                time.sleep(1)
            else:
                print('Первый ответ неправильный!')
                answer, resume_button = self.find_end_modal()
                r.mset({task_key: answer})
                self.driver.execute_script("arguments[0].click();", resume_button)
                time.sleep(1)


if __name__ == '__main__':

    cookies_list = [(file, num) for num, file in enumerate(os.listdir("cookies/"))]

    # function that calls the method on each instance
    def foo(file_num: list) -> list:
        file = file_num[0]

        if file.endswith(".pkl"):
            print(os.path.join("cookies/", file))

            try:
                game_s = GameSolver('cookies/' + file)
                game_s.start_game(free_play=True)
            except WebDriverException:
                game_s = GameSolver('cookies/' + file)
                game_s.start_game(free_play=True)

        return file_num

    # actually call functions and retrieve list of results
    p = Pool(3)
    results = p.map(foo, cookies_list)
    print(results)