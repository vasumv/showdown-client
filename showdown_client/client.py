import re
import logging

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from showdown_parser import Gamestate, Pokemon, Move, Switch

SHOWDOWN_URL = 'https://play.pokemonshowdown.com/'

NOT_ACTIVE_NICKNAME_FINE = r".+?\((?P<poke_name>.+?)\)$"
NOT_ACTIVE_NICKNAME = r".+?\((?P<poke_name>.+?)\) \((?P<health>(.+?%(\|.+?)?|fainted|tox|brn|slp|par))\)$"
NOT_ACTIVE_NO_NICKNAME_FINE = r"(?P<poke_name>.+?)$"
NOT_ACTIVE_NO_NICKNAME = r"(?P<poke_name>.+?) \((?P<health>(.+?%(\|.+?)?|fainted|tox|brn|slp|par))\)$"
ACTIVE_NO_NICKNAME = r"(?P<poke_name>.+) \(active\)$"
ACTIVE_NICKNAME = r".+\((?P<poke_name>.+?)\) \(active\)$"

CONDITIONS = set(["tox", "brn", "slp", "par"])

class StateException(Exception):

    def __init__(self, method, in_states, current_state):
        message = "Client tried calling <{method}> method while in [{current_state}]. Appropriate states: {states}".format(
            method=method,
            current_state=current_state,
            states=str(list(in_states))
        )
        super(StateException, self).__init__(message)

def require_state(in_states):
    if in_states is not None:
        in_states = set(in_states)
    def inner(func):
        def f(self, *args, **kwargs):
            if in_states is not None:
                if self.get_state() not in in_states:
                    raise StateException(func.__name__, in_states, self.get_state())
            result = func(self, *args, **kwargs)
            return result
        return f
    return inner

def state(in_states, out_state):
    if in_states is not None:
        in_states = set(in_states)
    def inner(func):
        def f(self, *args, **kwargs):
            if in_states is not None:
                if self.get_state() not in in_states:
                    raise StateException(func.__name__, in_states, self.get_state())
            result = func(self, *args, **kwargs)
            self.set_state(out_state)
            return result
        return f
    return inner


class ShowdownClient(object):

    def __init__(self, agent, browser='firefox', url=SHOWDOWN_URL, username=None, password=None):
        self.agent = agent
        self.browser = browser
        self.start_url = url
        self.state = None
        self.username = username
        self.password = password


        if self.browser == 'firefox':
            self.driver = webdriver.Firefox()
        elif self.browser == 'phantomjs':
            self.driver = webdriver.PhantomJS()
            self.driver.set_window_size(1920, 1080)

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def mute(self):
        logging.info("Muting sound...")
        sound_options = self.selector('[name="openSounds"]')
        sound_options.click()

        mute = self.selector('input[name="muted"]')
        mute.click()

        sound_options = self.selector('[name="openSounds"]')
        sound_options.click()

    @require_state(['battle_main', 'start_battle'])
    def chat(self, text):
        logging.info("Sending chat: %s" % text)
        chatbox = self.selector('form.chatbox')
        textbox = self.selectors('textarea', chatbox)[1]
        textbox.send_keys(text, Keys.ENTER)

    def screenshot(self, location):
        self.driver.save_screenshot(location)

    def wait(self, selector, time):
        wait = WebDriverWait(self.driver, time)
        try:
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            return element
        except:
            return None

    def selector(self, string, elem=None):
        try:
            elem = elem or self.driver
            return elem.find_element_by_css_selector(string)
        except:
            pass

    def selectors(self, string, elem=None):
        try:
            elem = elem or self.driver
            return elem.find_elements_by_css_selector(string)
        except:
            pass

    @state(None, 'homepage')
    def start(self):
        logging.info("Starting driver...")
        self.driver.get(self.start_url)
        self.driver.execute_script("localStorage.clear();")

    @state(None, 'stopped')
    def stop(self):
        logging.info("Stopping driver...")
        self.driver.quit()

    @state(None, 'homepage')
    def home(self):
        logging.info("Going to home page...")
        home_button = self.selector('[href="/"].button.roomtab')
        home_button.click()

    @state(['homepage'], 'homepage')
    def choose_name(self, username=None, password=None):
        username = username or self.username
        password = password or self.password
        logging.info("Logging in as %s..." % username)
        choose_button = self.wait('button[name="login"]', 3)
        choose_button.click()

        popup = self.selector('.ps-popup')

        user_input = self.selector('input[name="username"].textbox', popup)
        user_input.send_keys(username)

        submit_button = self.selector('button[type="submit"]', popup)
        submit_button.click()

        password_popup = self.wait('.ps-popup', 4)
        if password_popup is not None:
            password_field = self.selector('input[type="password"].textbox', password_popup)
            password_field.send_keys(password)

            login_button = self.selector('button[type="submit"]', password_popup)
            login_button.click()
        self.username = username

    @state(['homepage'], 'teambuilder')
    def teambuilder(self):
        logging.info("Going to Team Builder...")
        button = self.selector('button[value="teambuilder"].button')
        button.click()

    @state(['teambuilder'], 'teambuilder')
    def create_team(self, text, name=None):
        logging.info("Creating team...")
        new_team_button = self.selector('button[name="newTop"].button')
        new_team_button.click()

        self.select_team_format(tier='ou')

        import_button = self.selector('button[name="import"].button')
        import_button.click()

        team_edit = self.driver.find_element_by_css_selector(".teamedit textarea")
        team_edit.send_keys(text)

        if name is not None:
            team_name_edit = self.driver.find_element_by_css_selector("input.teamnameedit")
            team_name_edit.send_keys(Keys.CONTROL, "a")
            team_name_edit.send_keys(name)

        save_button = self.driver.find_element_by_css_selector("button[name='saveImport'].savebutton")
        save_button.click()

        back_button = self.driver.find_element_by_css_selector("button[name='back']")
        back_button.click()

    @state(['homepage'], 'homepage')
    def select_battle_format(self, tier='ou'):
        logging.info("Selecting battle tier...")
        add_button = self.selector('button[name="showSearchGroup"]')
        if add_button is not None:
            try:
                add_button.click()
            except:
                pass
        self.select_format(tier)

    def select_format(self, tier, team=False):
        if team:
            format_dropdown = self.selector('button[name="format"].select.formatselect.teambuilderformatselect')
        else:
            format_dropdown = self.selector('button[name="format"].select.formatselect')
        format_dropdown.click()

        popup = self.selector('.ps-popup')

        button = self.selector('button[name="selectFormat"][value="%s"]' % tier, popup)
        if button is not None:
            button.click()
        else:
            format_dropdown.click()


    @state(['teambuilder'], 'teambuilder')
    def select_team_format(self, tier='ou'):
        logging.info("Selecting team tier...")
        self.select_format(tier, team=True)

    @require_state(['start_battle', 'battle_main'])
    def get_legal_actions(self):
        actions = []
        battle = self.selector('.battle-controls')

        move_menu = self.selector('.movemenu', battle)
        if move_menu is not None:
            move_buttons = self.selectors('button', move_menu)
            for i, button in enumerate(move_buttons):
                if button.get_attribute('name') == "chooseMove":
                    if button.get_attribute('class') != "disabled":
                        actions.append(Move(button.get_attribute('data-move')))

        switch_menu = self.selector('.switchmenu', battle)
        switch_buttons = self.selectors('button', switch_menu)
        for button in switch_buttons:
            if button.get_attribute('name') in ['chooseSwitch', 'chooseTeamPreview']:
                if button.get_attribute('class') != "disabled":
                    hov = ActionChains(self.driver).move_to_element(button)
                    hov.perform()
                    tooltip = self.selector("#tooltipwrapper")
                    text = self.selector('h2', tooltip).text
                    match = re.match(r".+ \((?P<pokename>.+?)\)", text)
                    if match:
                        pokename = match.group('pokename')
                    else:
                        pokename = text
                    actions.append(Switch(pokename))
        return actions

    @require_state(['start_battle', 'battle_main'])
    def perform_action(self, action):
        battle = self.selector('.battle-controls')
        megaevo = self.selector('input[name="megaevo"]')
        if megaevo is not None:
            megaevo.click()
        if action.is_move():
            move_menu = self.selector('.movemenu', battle)
            if move_menu is not None:
                move_buttons = self.selectors('button', move_menu)
                for i, button in enumerate(move_buttons):
                    if button.get_attribute('name') == "chooseMove":
                        if button.get_attribute('data-move') == action.get_name():
                            button.click()
                            return True
        if action.is_switch():
            poke_name = action.get_name()
            switch_menu = self.selector('.switchmenu', battle)
            switch_buttons = self.selectors('button', switch_menu)
            for i, button in enumerate(switch_buttons):
                hov = ActionChains(self.driver).move_to_element(button)
                hov.perform()
                tooltip = self.selector("#tooltipwrapper")
                text = self.selector('h2', tooltip).text
                match = re.match(r".+ \((?P<pokename>.+?)\)", text)
                if match:
                    pokename = match.group('pokename')
                else:
                    pokename = text
                if pokename == poke_name:
                    button.click()
                    return True
        return False

    @state(['homepage'], 'homepage')
    def play(self, n_iters):
        logging.info("Playing %u battles..." % n_iters)
        for i in xrange(n_iters):
            self.battle()

    @state(['start_battle'], 'battle_main')
    def select_initial(self):
        self.make_action(initial=True)

    @require_state(['start_battle', 'battle_main'])
    def get_gamestate(self):
        battle = self.selector('.battle')
        my_trainer = self.selector('.trainer', self.selector('.leftbar', battle))
        opp_trainer = self.selector('.trainer', self.selector('.rightbar', battle))
        teams = ([], [])
        primary = [None, None]
        for i, icons in enumerate([self.selectors('.pokemonicon', my_trainer),
                                                     self.selectors('.pokemonicon', opp_trainer)]):
            for icon in icons:
                text = icon.get_attribute('title')
                if re.match(ACTIVE_NICKNAME, text):
                    match = re.match(ACTIVE_NICKNAME, text)
                    poke_name = match.group('poke_name')
                    faint = False
                    if i == 0:
                        statbar = self.selector('.statbar.rstatbar')
                    else:
                        statbar = self.selector('.statbar.lstatbar')
                    percent = self.selector('.hptext', statbar).text
                    primary[i] = poke_name
                elif re.match(ACTIVE_NO_NICKNAME, text):
                    match = re.match(ACTIVE_NO_NICKNAME, text)
                    poke_name = match.group('poke_name')
                    faint = False
                    if i == 0:
                        statbar = self.selector('.statbar.rstatbar')
                    else:
                        statbar = self.selector('.statbar.lstatbar')
                    percent = self.selector('.hptext', statbar).text
                    primary[i] = poke_name
                elif re.match(NOT_ACTIVE_NICKNAME, text):
                    match = re.match(NOT_ACTIVE_NICKNAME, text)
                    poke_name = match.group('poke_name')
                    if match.group('health') == 'fainted':
                        faint = True
                        percent = '0%'
                    else:
                        faint = False
                        percent = match.group('health').split('|')[0]
                        if percent in CONDITIONS:
                            percent = '100%'
                elif re.match(NOT_ACTIVE_NO_NICKNAME, text):
                    match = re.match(NOT_ACTIVE_NO_NICKNAME, text)
                    poke_name = match.group('poke_name')
                    if match.group('health') == 'fainted':
                        faint = True
                        percent = '0%'
                    else:
                        faint = False
                        percent = match.group('health').split('|')[0]
                        if percent in CONDITIONS:
                            percent = '100%'
                elif re.match(NOT_ACTIVE_NICKNAME_FINE, text):
                    match = re.match(NOT_ACTIVE_NICKNAME_FINE, text)
                    poke_name = match.group('poke_name')
                    faint = False
                    percent = '100%'
                else:
                    poke_name = text
                    faint = False
                    percent = '100%'
                health = float(percent[:-1]) / 100.0
                poke = Pokemon(poke_name, faint=faint, health=health)
                teams[i].append(poke)
        gamestate = Gamestate(teams=teams)
        for i, p in enumerate(primary):
            if p is not None:
                gamestate.set_primary(i, p)
        return gamestate

    def make_action(self, initial=False):
        gamestate = self.get_gamestate()
        actions = self.get_legal_actions()
        selected_action = self.agent.get_action(gamestate, actions, initial=initial)
        for action in actions:
            if action == selected_action:
                self.perform_action(action)

    @state(['homepage'], 'homepage')
    def battle(self):
        logging.info("Searching for battle...")
        add_button = self.selector('button[name="showSearchGroup"]')
        if add_button is not None:
            try:
                add_button.click()
            except:
                pass
        search_button = self.wait('button[name="search"]', 5)
        search_button.click()
        battle_controls = self.wait('.battle-controls', 60)
        logging.info("Battle started: %s" % self.driver.current_url)
        self.set_state('start_battle')
        self.chat('gl hf')
        what_do = self.selector('.whatdo', battle_controls)
        if what_do is not None and what_do.text == 'How will you start the battle?':
            self.select_initial()
        save_replay = self.selector('button[name="saveReplay"]')
        start_timer = False
        while save_replay is None:
            while not self.wait('.switchmenu', 1) and save_replay is None:
                timer = self.selector('button[name="setTimer"]')
                if timer is not None and not start_timer:
                    start_timer = True
                    timer.click()
                save_replay = self.selector('button[name="saveReplay"]')
            if save_replay is None:
                self.make_action()
        self.chat('gg')
        save_replay = self.selector('button[name="saveReplay"]')
        save_replay.click()
        logging.info("Battle complete! Saving replay...")
        overlay = self.wait('.ps-overlay', 60)
        close_button = self.selector('button[name="close"]', overlay)
        close_button.click()

        close_buttons = self.selectors(".closebutton")
        while len(close_buttons) > 0:
            close_buttons[0].click()
            close_buttons = self.selectors(".closebutton")
        self.home()
