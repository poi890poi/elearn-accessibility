import logging.handlers
import time
import traceback
import os.path
import sys
import logging
import logging.handlers
from collections.abc import Callable, Awaitable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import *
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions

from config import *


browser = None
logger = logging.getLogger(__name__)

def list_script_src():
    global browser, logger
    scripts = browser.find_elements(By.TAG_NAME, 'script')
    for s_ in scripts:
        logger.info(s_.get_attribute('src'))

def switch_to_right_panel():
    global browser, logger
    browser.switch_to.default_content()
    f_ = browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frameset/frame[@id="s_main"]')
    browser.switch_to.frame(f_)

def switch_to_left_panel():
    global browser, logger
    browser.switch_to.default_content()
    f_ = browser.find_element(By.XPATH, 'html/frameset/frameset/frame[@id="moocSysbar"]')
    browser.switch_to.frame(f_)

def submit_answers():
    global browser, logger
    submit = browser.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
    submit.click()
    browser.implicitly_wait(60)
    for _ in range(2):
        try:
            wait = WebDriverWait(browser, timeout=2)
            alert = wait.until(lambda d : d.switch_to.alert)
            alert.accept()
        except NoAlertPresentException:
            ...

def switch_to_new_window():
    global browser, logger
    try:
        wait = WebDriverWait(browser, timeout=2)
        wait.until(expected_conditions.number_of_windows_to_be(2))
    except TimeoutException:
        logger.warning('Unable to find window.')
        return
    for w_ in browser.window_handles:
        logger.info('window', w_.title)
    browser.switch_to.window(browser.window_handles[1])

def exam_left_attempt() -> bool:
    '''
    The exam is opened from the left panel.
    '''
    global browser, logger
    logger.info('Perform test from left panel.')
    success = False

    # This is not working because the questions are randomized and answers are not provided.
    # return is_test

    switch_to_left_panel()
    moocSidebar = browser.find_element(By.ID, 'moocSidebar')
    exam = moocSidebar.find_element(By.PARTIAL_LINK_TEXT, '測驗')
    exam.click()
    browser.implicitly_wait(60)

    switch_to_right_panel()
    onclicks = browser.find_elements(By.CSS_SELECTOR, 'div[onclick]')
    for c_ in onclicks:
        if 'togo' in c_.get_attribute('onclick'):
            browser.execute_script(c_.get_attribute('onclick'))
            break
    browser.implicitly_wait(60)

    switch_to_new_window()

    examBegin = browser.find_element(By.CSS_SELECTOR, 'input[value="開始作答"]')
    examBegin.click()

    questions = browser.find_elements(By.CSS_SELECTOR, 'ol[type="a"]')
    for q_ in questions:
        logger.info('Q: {}'.format(q_.find_element(By.XPATH, './..').text))
        # a_ = int(ANS_OPTIONS[answers[aindex]][-1]) - 1
        options = q_.find_elements(By.TAG_NAME, 'input')
        for o_ in options:
            logger.debug(o_.find_element(By.XPATH, './../..').text)
        options[-1].click()
        # print(q_, ANS_OPTIONS[answers[aindex]], a_, len(options))
        # options[a_].click()
        # aindex += 1

    submit_answers()
    print('Test submitted.')

    wait = WebDriverWait(browser, timeout=60)
    wait.until(expected_conditions.url_contains('/view_result.php'))

    form = browser.find_element(By.TAG_NAME, 'form')
    try:
        result = form.find_element(By.TAG_NAME, 'span')
        if '不及格' not in result.text:
            logger.info('Test passed.')
            success = True
    except NoSuchElementException:
        ...
    browser.implicitly_wait(60)

    browser.close()
    browser.switch_to.window(browser.window_handles[0])

    return success

def exam_left():
    global browser, logger
    retry_count = 10
    while retry_count:
        if exam_left_attempt(): break
        retry_count -= 1

def exam_right() -> bool:
    '''
    The exam is opened from the right panel, as a lesson.
    '''
    global browser, logger
    is_test = False
    try:
        browser.execute_script('go(goExam,500);')
        browser.implicitly_wait(5)
        logger.info('Performing test...')
        is_test = True
        exam_index = 0
        while True:
            try:
                # Answer the question...
                q_ = browser.execute_script('return data["DocumentElement"]["Exam"][{}]["Question"];'.format(exam_index)).strip()
                ans_ = browser.execute_script('return data["DocumentElement"]["Exam"][{}]["Answer"];'.format(exam_index)).strip()
                if ans_:
                    try:
                        ans_ = ans_.replace('(', '').upper()
                        a_ = ANS_OPTIONS[ans_[0]]
                        logger.info('Answer {} selected for question {}.'.format(ans_, q_))
                        option = browser.find_element(By.ID, a_)
                        wait = WebDriverWait(browser, timeout=1800)
                        wait.until(lambda d : option.is_displayed())
                        browser.execute_script('selected(document.getElementById("{}").firstChild,{});'.format(a_, a_[-1]))
                    except (IndexError, KeyError):
                        pass
                ansbtn = browser.find_element(By.CSS_SELECTOR, '#container span.ansbtn')
                wait = WebDriverWait(browser, timeout=1800)
                wait.until(lambda d : ansbtn.is_displayed())
                browser.execute_script('check();')
                browser.implicitly_wait(5)
                exam_index += 1
                try:
                    resultbtn = browser.find_element(By.CSS_SELECTOR, '#container span.resultbtn')
                    wait = WebDriverWait(browser, timeout=2)
                    wait.until(lambda d : resultbtn.is_displayed())
                    browser.execute_script('defaultOption();go(goResult,500);')
                    logger.info('Test passed.')
                    break
                except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                    ...
                try:
                    rebtn = browser.find_element(By.CSS_SELECTOR, '#container span.rebtn')
                    wait = WebDriverWait(browser, timeout=2)
                    wait.until(lambda d : rebtn.is_displayed())
                    score = browser.find_element(By.CSS_SELECTOR, '#container span.score')
                    score = score.get_attribute('class')
                    if 'pass_color' in score:
                        logger.info('Test passed.')
                        break
                    elif 'nopass_color' in score:
                        logger.warning('Test failed. Please re-test.')
                        browser.execute_script('go(goIntro,500);')
                        browser.implicitly_wait(5)
                except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                    ...
                browser.execute_script('nextExam();')
                browser.implicitly_wait(5)
            except (NoSuchElementException, StaleElementReferenceException):
                ...
            time.sleep(1)
    except (NoSuchElementException, JavascriptException):
        ...    
    return is_test

def questionnaire():
    global browser, logger
    logger.info('Questionnaire...')
    switch_to_left_panel()
    moocSidebar = browser.find_element(By.ID, 'moocSidebar')
    q_ = moocSidebar.find_element(By.PARTIAL_LINK_TEXT, '問卷')
    q_.click()
    browser.implicitly_wait(60)

    switch_to_right_panel()
    begin = browser.find_element(By.CSS_SELECTOR, 'div[onclick]')
    browser.execute_script(begin.get_attribute('onclick'))
    browser.implicitly_wait(60)

    switch_to_new_window()

    questions = browser.find_elements(By.CSS_SELECTOR, 'ol[type="a"]')
    for q_ in questions:
        options = q_.find_elements(By.TAG_NAME, 'input')
        options[0].click()

    submit_answers()
    browser.switch_to.window(browser.window_handles[0])
    logger.info('Questionnaire submitted.')

def wait_video_finish(duration: float, func: Callable[[], None],
                      driver_wait: Callable[[], None] = None):
    global browser, logger
    timeout = time.time() + duration
    while True and duration:
        ActionChains(browser) \
            .move_by_offset(0, 15) \
            .perform()
        if driver_wait:
            try:
                wait = WebDriverWait(browser, timeout=2)
                wait.until(driver_wait)
                break
            except TimeoutException:
                ...
        elif func():
            break
        if time.time() >= timeout:
            logger.warning(f'Video playback timed out. duration={duration}')
            break
        time.sleep(2)
        ActionChains(browser) \
            .move_by_offset(0, -15) \
            .perform()

def video_play_jp(lesson: str, title: str):
    global browser, logger
    try:
        browser.execute_script('dashPlayer.isReady();')
    except JavascriptException:
        return
    logger.info('Playing video {} ({}) with JP player (DashPlayer)...'.format(lesson, title))
    timeout = time.time() + 60
    duration = 0
    while True:
        if browser.execute_script('return dashPlayer.isReady();'):
            duration = browser.execute_script("return document.getElementsByTagName('video')[0].duration;")
            browser.execute_script('dashPlayer.setMute(true);')
            browser.execute_script(f'dashPlayer.setPlaybackRate({PLAYBACK_RATE});')
            browser.execute_script('dashPlayer.play();')
            break
        if time.time() > timeout:
            logger.warning('dashPlayer initialization timed out.')
            break
        time.sleep(2)
    wait_video_finish(duration, func = lambda : browser.execute_script('return dashPlayer.isPaused();'))

def video_play_mp(lesson: str, title: str):
    global browser, logger
    logger.info('Playing video {} ({}) with MP player...'.format(lesson, title))

    # Set video playback speed
    mv = browser.find_element(By.ID, 'mv')
    video = mv.find_element(By.TAG_NAME, 'video')
    try:
        wait = WebDriverWait(browser, timeout=60)
        wait.until(lambda d : browser.execute_script("return (typeof cPb !== 'undefined');"))
        browser.execute_script(f'cPb.SetSpeed({PLAYBACK_RATE});')
        browser.execute_script('cPb.SetVol(0);')
    except JavascriptException:
        logger.error(traceback.format_exc())

    # Check playback finished
    time.sleep(5)
    ply_play = browser.find_element(By.ID, 'ply_play')
    ply_pause = browser.find_element(By.ID, 'ply_pause')
    duration = browser.execute_script("return document.getElementsByTagName('video')[0].duration;")
    wait_video_finish(duration, func = lambda : browser.execute_script('return (cPb.time===-1);'))
    # wait_video_finish(duration, driver_wait = lambda : ply_play.is_displayed())

def video_play(lesson: str, title: str) -> PlayerType:
    global browser, logger
    player_type = PlayerType.INVALID
    try:
        scoMainFrame = browser.find_element(By.NAME, 'scoMainFrame')
        browser.switch_to.frame(scoMainFrame)
        player_type = PlayerType.MP
        video_play_mp(lesson, title)
    except NoSuchElementException:
        ...
    try:
        f_ = browser.find_element(By.TAG_NAME, 'iframe')
        browser.switch_to.frame(f_)
        player_type = PlayerType.JP
        video_play_jp(lesson, title)
    except NoSuchElementException:
        ...
    logger.info(f'Video {title} finished.')
    return player_type

def login():
    # Login
    global browser, logger
    accountlinkbt = browser.find_element(By.ID, 'accountlinkbt')
    accountlinkbt.click()
    txt_account = browser.find_element(By.ID, 'AccountPassword_simple_txt_account')
    txt_password = browser.find_element(By.ID, 'AccountPassword_simple_txt_password')
    btn_LoginHandler = browser.find_element(By.ID, 'AccountPassword_simple_btn_LoginHandler')
    txt_account.send_keys(USERNAME)
    txt_password.send_keys(PASSWORD)
    btn_LoginHandler.click()

def apply(course: str):
    global browser, logger
    course_action = browser.find_element(By.CSS_SELECTOR, '.course-action button')
    if '報名' in course_action.text:
        browser.execute_script("enployCourse('{}');".format(os.path.split(course)[-1]))
        btn_success = browser.find_element(By.CSS_SELECTOR, '.modal-footer button.btn-success')
        btn_success.click()
        browser.implicitly_wait(30)
    else:
        logger.debug('course_action.text='.format(course_action.text))
    browser.execute_script("gotoCourse('{}');".format(os.path.split(course)[-1]))
    browser.implicitly_wait(30)

def switch_to_pathtree():
    global browser, logger
    browser.switch_to.default_content()
    f_ = browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frameset/frame[@id="s_catalog"]')
    browser.switch_to.frame(f_)
    pathtree = browser.find_element(By.ID, 'pathtree')
    browser.switch_to.frame(pathtree)

def get_coursename() -> str:
    global browser, logger
    f_ = browser.find_element(By.XPATH, 'html/frameset/frameset/frameset/frame[@id="s_sysbar"]')
    browser.switch_to.frame(f_)
    coursename = browser.find_element(By.CLASS_NAME, 'coursename')
    return coursename.text

def learn(course: str, answers: str):
    # Open course page then login
    global browser, logger
    if WEBDRIVER == WebDriverType.CHROME:
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--incognito')
        browser = webdriver.Chrome(options=chrome_options)
    elif WEBDRIVER == WebDriverType.EDGE:
        browser = webdriver.Edge()

    logger.info('Opening course at {}'.format(course))
    browser.get(course)
    browser.implicitly_wait(30)

    course_info_bottom = browser.find_element(By.ID, 'course-info-bottom')
    gotoCourse = course_info_bottom.find_element(By.TAG_NAME, 'button')
    gotoCourse.click()
    browser.execute_script("location.href='https://www.cp.gov.tw/portal/Clogin.aspx?ReturnUrl=https%3A%2F%2Felearn.hrd.gov.tw%2Fegov_login.php'")

    login()

    try:
        browser.execute_script("location.href='{}'".format(course))
        time.sleep(15)
    except UnexpectedAlertPresentException:
        try:
            wait = WebDriverWait(browser, timeout=30)
            alert = wait.until(lambda d : d.switch_to.alert)
            alert.accept()
        except NoAlertPresentException:
            ...
    browser.implicitly_wait(30)

    apply(course)

    WebDriverWait(webdriver, 30).until(
        lambda driver: browser.execute_script("return document.readyState") == "complete")

    coursename = get_coursename()
    logger.info(f'Opening course {coursename} ({course})...')

    switch_to_pathtree()

    displayPanel = browser.find_element(By.ID, 'displayPanel')
    items = displayPanel.find_elements(By.TAG_NAME, 'a')
    launch_activities = [(i_.get_attribute('onclick'), i_.get_attribute('title')) for i_ in items]
    for a_, t_ in launch_activities[1:]:
        if 'launchActivity' in a_:
            browser.execute_script(a_)
            browser.implicitly_wait(60)

            try:
                switch_to_right_panel()
                if video_play(a_, t_) == PlayerType.INVALID:
                    if exam_right(): break
            except (NoSuchElementException, JavascriptException):
                logger.error(traceback.format_exc())
        switch_to_pathtree()

    exam_left()
    questionnaire()

    browser.implicitly_wait(30)
    browser.close()
    logger.info(f'Course {coursename} finished.')
    del browser

def init_logger():
    global logger
    os.makedirs('logs', exist_ok=True)

    formatter = logging.Formatter(u"%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

    fileHandler = logging.handlers.RotatingFileHandler(
        'logs/log', maxBytes=8000, backupCount=10, encoding='utf-8')
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    logger.setLevel(logging.INFO)
    logger.info('Logger is initiated.')


if __name__ == '__main__':
    init_logger()
    for c_, a_, *_ in COURSES:
        learn(c_, a_)