import logging.handlers
import time
import traceback
import os.path
import sys
import logging
import logging.handlers
import json
from collections.abc import Callable, Awaitable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
import selenium.webdriver.common.keys as keys

from config import *
from examiner import E as Examiner


class A():
    browser = None
    logger = logging.getLogger(__name__)
    cache = dict()
    windows = dict()

    @staticmethod
    def init_browser():
        if WEBDRIVER == WebDriverType.CHROME:
            chrome_options = webdriver.ChromeOptions()
            # chrome_options.add_argument('--blink-settings=imagesEnabled=false')
            chrome_options.add_argument('--incognito')
            A.browser = webdriver.Chrome(options=chrome_options)
        elif WEBDRIVER == WebDriverType.EDGE:
            A.browser = webdriver.Edge()

    @staticmethod
    def init_logger():
        os.makedirs('logs', exist_ok=True)

        formatter = logging.Formatter(u"[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
                                    #   "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

        fileHandler = logging.handlers.RotatingFileHandler(
            'logs/log', maxBytes=8000, backupCount=10, encoding='utf-8')
        fileHandler.setFormatter(formatter)
        A.logger.addHandler(fileHandler)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        A.logger.addHandler(consoleHandler)

        A.logger.setLevel(logging.DEBUG)
        A.logger.info('Logger is initiated.')

    @staticmethod
    def list_script_src():
        scripts = A.browser.find_elements(By.TAG_NAME, 'script')
        for s_ in scripts:
            A.logger.info(s_.get_attribute('src'))

    @staticmethod
    def switch_to_right_panel():
        A.browser.switch_to.default_content()
        f_ = A.browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frameset/frame[@id="s_main"]')
        A.browser.switch_to.frame(f_)

    @staticmethod
    def switch_to_left_panel():
        A.browser.switch_to.default_content()
        f_ = A.browser.find_element(By.XPATH, 'html/frameset/frameset/frame[@id="moocSysbar"]')
        A.browser.switch_to.frame(f_)

    @staticmethod
    def submit_answers():
        submit = A.browser.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        submit.click()
        A.browser.implicitly_wait(60)
        for _ in range(2):
            try:
                wait = WebDriverWait(A.browser, timeout=2)
                alert = wait.until(lambda d : d.switch_to.alert)
                alert.accept()
            except NoAlertPresentException:
                ...

    @staticmethod
    def switch_to_new_window(expected_wnd_count: int):
        print(f'expected_wnd_count={expected_wnd_count}, current={len(A.browser.window_handles)}')
        for i_, w_ in enumerate(A.browser.window_handles):
            A.logger.debug(f'window {i_}: title={w_.title()}')
        try:
            wait = WebDriverWait(A.browser, timeout=30)
            wait.until(expected_conditions.number_of_windows_to_be(expected_wnd_count))
        except TimeoutException:
            A.logger.warning('Unable to find new window.')
            return
        target = A.browser.window_handles[-1]
        A.logger.info(f'Switch to window {target.title()}')
        A.browser.switch_to.window(target)

    @staticmethod
    def exam_left_attempt() -> bool:
        '''
        The exam is opened from the left panel.
        '''
        A.logger.info('Perform test from left panel.')
        success = False

        # This is not working because the questions are randomized and answers are not provided.
        # return is_test

        A.switch_to_left_panel()
        moocSidebar = A.browser.find_element(By.ID, 'moocSidebar')
        exam = moocSidebar.find_element(By.PARTIAL_LINK_TEXT, '測驗')
        exam.click()
        A.browser.implicitly_wait(60)

        wndcount = len(A.browser.window_handles)

        A.switch_to_right_panel()
        onclicks = A.browser.find_elements(By.CSS_SELECTOR, 'div[onclick]')
        for c_ in onclicks:
            if 'togo' in c_.get_attribute('onclick'):
                A.browser.execute_script(c_.get_attribute('onclick'))
                break
        A.browser.implicitly_wait(60)

        A.switch_to_new_window(wndcount + 1)

        examBegin = A.browser.find_element(By.CSS_SELECTOR, 'input[value="開始作答"]')
        examBegin.click()

        qwnd = A.browser.current_window_handle
        questions = A.browser.find_elements(By.CSS_SELECTOR, 'ol[type="a"]')
        qtxts = []
        for q_ in questions:
            A.logger.info('Q: {}'.format(q_.find_element(By.XPATH, './..').text))
            qtxt = [q_.find_element(By.XPATH, './..').text]
            aindex = 0
            options = q_.find_elements(By.TAG_NAME, 'input')
            for o_ in options:
                A.logger.debug(o_.find_element(By.XPATH, './../..').text)
                qtxt.append(str(aindex) + ': ' + o_.find_element(By.XPATH, './../..').text)
                aindex += 1
            if len(qtxt) == 3 and qtxt[1].strip() == '0:' and qtxt[2].strip() == '1:':
                qtxt[1] = '0: 是'
                qtxt[2] = '1: 否'
            qtxt = '\n'.join(qtxt)
            qtxts.append(qtxt)
            A.logger.debug(qtxt)

            a_ = Examiner.query(qtxt)
            A.logger.debug('A: ' + a_)
            a_ = int(''.join(c for c in a_ if c.isdigit()))
            options[a_].click()

        for q_ in qtxts:
            a_ = Examiner.query(q_)
            a_ = int(''.join(c for c in a_ if c.isdigit()))

        A.submit_answers()
        print('Test submitted.')

        wait = WebDriverWait(A.browser, timeout=60)
        wait.until(expected_conditions.url_contains('/view_result.php'))

        form = A.browser.find_element(By.TAG_NAME, 'form')
        try:
            result = form.find_element(By.TAG_NAME, 'span')
            if '不及格' not in result.text:
                A.logger.info('Test passed.')
                success = True
        except NoSuchElementException:
            ...
        A.browser.implicitly_wait(60)

        A.browser.close()
        A.browser.switch_to.window(A.windows[WindowHandle.COURSE])

        return success

    @staticmethod
    def exam_left() -> bool:
        retry_count = 1
        while retry_count:
            if A.exam_left_attempt():
                return True
            retry_count -= 1
        return False

    @staticmethod
    def exam_right() -> bool:
        '''
        The exam is opened from the right panel, as a lesson.
        '''
        success = False
        try:
            A.browser.execute_script('go(goExam,500);')
            A.browser.implicitly_wait(5)
            A.logger.info('Performing test...')
            success = False
            exam_index = 0
            while True:
                try:
                    # Answer the question...
                    q_ = A.browser.execute_script('return data["DocumentElement"]["Exam"][{}]["Question"];'.format(exam_index)).strip()
                    ans_ = A.browser.execute_script('return data["DocumentElement"]["Exam"][{}]["Answer"];'.format(exam_index)).strip()
                    if ans_:
                        try:
                            ans_ = ans_.replace('(', '').upper()
                            a_ = ANS_OPTIONS[ans_[0]]
                            A.logger.info('Answer {} selected for question {}.'.format(ans_, q_))
                            option = A.browser.find_element(By.ID, a_)
                            wait = WebDriverWait(A.browser, timeout=1800)
                            wait.until(lambda d : option.is_displayed())
                            A.browser.execute_script('selected(document.getElementById("{}").firstChild,{});'.format(a_, a_[-1]))
                        except (IndexError, KeyError):
                            pass
                    ansbtn = A.browser.find_element(By.CSS_SELECTOR, '#container span.ansbtn')
                    wait = WebDriverWait(A.browser, timeout=1800)
                    wait.until(lambda d : ansbtn.is_displayed())
                    A.browser.execute_script('check();')
                    A.browser.implicitly_wait(5)
                    exam_index += 1
                    try:
                        resultbtn = A.browser.find_element(By.CSS_SELECTOR, '#container span.resultbtn')
                        wait = WebDriverWait(A.browser, timeout=2)
                        wait.until(lambda d : resultbtn.is_displayed())
                        A.browser.execute_script('defaultOption();go(goResult,500);')
                        A.logger.info('Test passed.')
                        break
                    except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                        ...
                    try:
                        rebtn = A.browser.find_element(By.CSS_SELECTOR, '#container span.rebtn')
                        wait = WebDriverWait(A.browser, timeout=2)
                        wait.until(lambda d : rebtn.is_displayed())
                        score = A.browser.find_element(By.CSS_SELECTOR, '#container span.score')
                        score = score.get_attribute('class')
                        if 'pass_color' in score:
                            A.logger.info('Test passed.')
                            success = True
                            break
                        elif 'nopass_color' in score:
                            A.logger.warning('Test failed. Please re-test.')
                            A.browser.execute_script('go(goIntro,500);')
                            A.browser.implicitly_wait(5)
                    except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                        ...
                    A.browser.execute_script('nextExam();')
                    A.browser.implicitly_wait(5)
                except (NoSuchElementException, StaleElementReferenceException):
                    ...
                time.sleep(1)
        except (NoSuchElementException, JavascriptException):
            ...    
        return success

    @staticmethod
    def questionnaire():
        A.logger.info('Questionnaire...')
        A.switch_to_left_panel()
        moocSidebar = A.browser.find_element(By.ID, 'moocSidebar')
        q_ = moocSidebar.find_element(By.PARTIAL_LINK_TEXT, '問卷')
        q_.click()
        A.browser.implicitly_wait(60)

        wndcount = len(A.browser.window_handles)

        A.switch_to_right_panel()
        begin = A.browser.find_element(By.CSS_SELECTOR, 'div[onclick]')
        A.browser.execute_script(begin.get_attribute('onclick'))
        A.browser.implicitly_wait(60)

        A.switch_to_new_window(wndcount + 1)

        questions = A.browser.find_elements(By.CSS_SELECTOR, 'ol[type="a"]')
        for q_ in questions:
            options = q_.find_elements(By.TAG_NAME, 'input')
            options[0].click()

        A.submit_answers()
        A.browser.switch_to.window(A.windows[WindowHandle.COURSE])
        A.logger.info('Questionnaire submitted.')

    @staticmethod
    def wait_video_finish(duration: float, func: Callable[[], None],
                        driver_wait: Callable[[], None] = None):
        timeout = time.time() + duration
        while True and duration:
            ActionChains(A.browser) \
                .move_by_offset(0, 15) \
                .perform()
            if driver_wait:
                try:
                    wait = WebDriverWait(A.browser, timeout=2)
                    wait.until(driver_wait)
                    break
                except TimeoutException:
                    ...
            elif func():
                break
            if time.time() >= timeout:
                A.logger.warning(f'Video playback timed out. duration={duration}')
                break
            time.sleep(2)
            ActionChains(A.browser) \
                .move_by_offset(0, -15) \
                .perform()

    @staticmethod
    def video_play_jp(lesson: str, title: str) -> bool:
        try:
            A.browser.execute_script('dashPlayer.isReady();')
        except JavascriptException:
            return False
        A.logger.info('Playing video {} ({}) with JP player (DashPlayer)...'.format(lesson, title))
        timeout = time.time() + 60
        duration = 0
        while True:
            if A.browser.execute_script('return dashPlayer.isReady();'):
                duration = A.browser.execute_script("return document.getElementsByTagName('video')[0].duration;")
                A.browser.execute_script('dashPlayer.setMute(true);')
                A.browser.execute_script(f'dashPlayer.setPlaybackRate({PLAYBACK_RATE});')
                A.browser.execute_script('dashPlayer.play();')
                break
            if time.time() > timeout:
                A.logger.warning('dashPlayer initialization timed out.')
                break
            time.sleep(2)
        A.wait_video_finish(duration, func = lambda : A.browser.execute_script('return dashPlayer.isPaused();'))
        return True

    @staticmethod
    def video_play_mp(lesson: str, title: str):
        A.logger.info('Playing video {} ({}) with MP player...'.format(lesson, title))

        # Set video playback speed
        mv = A.browser.find_element(By.ID, 'mv')
        video = mv.find_element(By.TAG_NAME, 'video')
        try:
            wait = WebDriverWait(A.browser, timeout=60)
            wait.until(lambda d : A.browser.execute_script("return (typeof cPb !== 'undefined');"))
            A.browser.execute_script(f'cPb.SetSpeed({PLAYBACK_RATE});')
            A.browser.execute_script('cPb.SetVol(0);')
        except JavascriptException:
            A.logger.error(traceback.format_exc())

        # Check playback finished
        time.sleep(5)
        ply_play = A.browser.find_element(By.ID, 'ply_play')
        ply_pause = A.browser.find_element(By.ID, 'ply_pause')
        duration = A.browser.execute_script("return document.getElementsByTagName('video')[0].duration;")
        A.wait_video_finish(duration, func = lambda : A.browser.execute_script('return (cPb.time===-1);'))

    @staticmethod
    def video_play(lesson: str, title: str) -> PlayerType:
        player_type = PlayerType.INVALID
        try:
            scoMainFrame = A.browser.find_element(By.NAME, 'scoMainFrame')
            A.browser.switch_to.frame(scoMainFrame)
            A.video_play_mp(lesson, title)
            player_type = PlayerType.MP
        except NoSuchElementException:
            ...
        try:
            f_ = A.browser.find_element(By.TAG_NAME, 'iframe')
            A.browser.switch_to.frame(f_)
            if A.video_play_jp(lesson, title):
                player_type = PlayerType.JP
        except NoSuchElementException:
            ...
        A.logger.info(f'Video {title} finished.')
        return player_type

    @staticmethod
    def login():
        # Login
        accountlinkbt = A.browser.find_element(By.ID, 'accountlinkbt')
        accountlinkbt.click()
        txt_account = A.browser.find_element(By.ID, 'AccountPassword_simple_txt_account')
        txt_password = A.browser.find_element(By.ID, 'AccountPassword_simple_txt_password')
        btn_LoginHandler = A.browser.find_element(By.ID, 'AccountPassword_simple_btn_LoginHandler')
        txt_account.send_keys(USERNAME)
        txt_password.send_keys(PASSWORD)
        btn_LoginHandler.click()

    @staticmethod
    def apply(course: str):
        course_action = A.browser.find_element(By.CSS_SELECTOR, '.course-action button')
        if '報名' in course_action.text:
            A.browser.execute_script("enployCourse('{}');".format(os.path.split(course)[-1]))
            btn_success = A.browser.find_element(By.CSS_SELECTOR, '.modal-footer button.btn-success')
            btn_success.click()
            A.browser.implicitly_wait(30)
        else:
            A.logger.debug('course_action.text='.format(course_action.text))
        A.browser.execute_script("gotoCourse('{}');".format(os.path.split(course)[-1]))
        A.browser.implicitly_wait(60)

    @staticmethod
    def switch_to_pathtree():
        A.browser.switch_to.default_content()
        f_ = A.browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frameset/frame[@id="s_catalog"]')
        A.browser.switch_to.frame(f_)
        pathtree = A.browser.find_element(By.ID, 'pathtree')
        A.browser.switch_to.frame(pathtree)

    @staticmethod
    def get_coursename() -> str:
        f_ = A.browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frame[@id="s_sysbar"]')
        A.browser.switch_to.frame(f_)
        coursename = A.browser.find_element(By.CLASS_NAME, 'coursename')
        return coursename.text

    @staticmethod
    def load_cache():
        try:
            with open('logs/cache.json', 'r', encoding='utf-8') as fp:
                A.cache = json.load(fp)
        except (FileNotFoundError, json.JSONDecodeError):
            ...

    @staticmethod
    def save_cache():
        with open('logs/cache.json', 'w', encoding='utf-8') as fp:
            json.dump(A.cache, fp, indent=4)

    @staticmethod
    def close_alerts(explicit_wait: bool = False):
        if explicit_wait:
            while True:
                try:
                    wait = WebDriverWait(A.browser, timeout=30)
                    alert = wait.until(lambda d : d.switch_to.alert)
                    alert.accept()
                    break
                except NoAlertPresentException:
                    time.sleep(2)
        while True:
            try:
                wait = WebDriverWait(A.browser, timeout=30)
                alert = wait.until(lambda d : d.switch_to.alert)
                alert.accept()
            except NoAlertPresentException:
                break


    @staticmethod
    def learn(course: str, answers: str):
        # Open course page then login
        courseid = os.path.split(course)[-1]
        try:
            if A.cache[courseid]['passed']:
                coursename = A.cache[courseid]['name']
                A.logger.info(f'Course {course}: {coursename} passed already; skip.')
                return
        except KeyError:
            ...
        A.init_browser()

        wndcount = len(A.browser.window_handles)
        A.browser.execute_script('window.open("");')
        A.switch_to_new_window(wndcount + 1)

        A.logger.info('Opening course at {}'.format(course))
        A.browser.get(course)
        A.browser.implicitly_wait(60)
        A.windows[WindowHandle.COURSE] = A.browser.current_window_handle

        course_info_bottom = A.browser.find_element(By.ID, 'course-info-bottom')
        gotoCourse = course_info_bottom.find_element(By.TAG_NAME, 'button')
        gotoCourse.click()
        A.browser.execute_script("location.href='https://www.cp.gov.tw/portal/Clogin.aspx?ReturnUrl=https%3A%2F%2Felearn.hrd.gov.tw%2Fegov_login.php'")

        A.login()

        try:
            A.browser.execute_script("location.href='{}'".format(course))
            time.sleep(15)
        except UnexpectedAlertPresentException:
            try:
                wait = WebDriverWait(A.browser, timeout=30)
                alert = wait.until(lambda d : d.switch_to.alert)
                alert.accept()
            except NoAlertPresentException:
                ...
        A.browser.implicitly_wait(60)

        A.apply(course)

        WebDriverWait(webdriver, 60).until(
            lambda driver: A.browser.execute_script("return document.readyState") == "complete")

        coursename = A.get_coursename()
        A.logger.info(f'Opening course {coursename} ({course})...')
        if courseid not in A.cache: A.cache[courseid] = {
            'id': courseid,
            'name': coursename,
            'url': course,
            'lessons': dict(),
        }

        A.switch_to_pathtree()

        displayPanel = A.browser.find_element(By.ID, 'displayPanel')
        items = displayPanel.find_elements(By.TAG_NAME, 'a')
        launch_activities = [(i_.get_attribute('onclick'), i_.get_attribute('title')) for i_ in items]
        for a_, t_ in launch_activities[1:]:
            if 'launchActivity' in a_:
                A.browser.execute_script(a_)
                A.browser.implicitly_wait(60)

                lessonid = a_.split(',')[-2]
                try:
                    if A.cache[courseid]['lessons'][lessonid]['played']:
                        lessonname = A.cache[courseid]['lessons'][lessonid]['name']
                        A.logger.info(f'Lesson {lessonid}: {lessonname} played already; skip.')
                        continue
                except KeyError:
                    ...
                if lessonid not in A.cache[courseid]['lessons']:
                    A.cache[courseid]['lessons'][lessonid] = {
                        'id': lessonid,
                        'name': t_,
                    }

                try:
                    A.switch_to_right_panel()
                    ptype = A.video_play(a_, t_)
                    if ptype == PlayerType.INVALID:
                        if A.exam_right():
                            A.cache[courseid]['passed'] = True
                            break
                    else:
                        A.cache[courseid]['lessons'][lessonid]['played'] = True
                        A.cache[courseid]['lessons'][lessonid]['player'] = ptype.name
                        A.save_cache()
                except (NoSuchElementException, JavascriptException):
                    A.logger.error(traceback.format_exc())
            A.switch_to_pathtree()

        if A.exam_left():
            A.cache[courseid]['passed'] = True
        A.questionnaire()

        A.cache[courseid]['qsubmitted'] = True
        A.save_cache()

        A.browser.implicitly_wait(30)
        A.browser.close()
        A.logger.info(f'Course {coursename} finished.')
        del A.browser

if __name__ == '__main__':
    A.init_logger()
    A.load_cache()
    for c_, a_, *_ in COURSES:
        A.learn(c_, a_)