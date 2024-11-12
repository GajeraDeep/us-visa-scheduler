import sys
import traceback
import time
import json
import random
import requests
import yaml
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from embassy import Embassies


def read_config(file_path):
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
    return config


config = read_config("config.yaml")

STEP_TIME = 0.5
SESSION_RESTART_TIME = 1800
JS_SCRIPT = (
    "var req = new XMLHttpRequest();"
    f"req.open('GET', '%s', false);"
    "req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');"
    "req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');"
    f"req.setRequestHeader('Cookie', '_yatri_session=%s');"
    "req.send(null);"
    "return req.responseText;"
)


class User:
    def __init__(self, user):
        self.username = user.get("username")
        self.password = user.get("password")
        self.schedule_id = user.get("schedule_id")
        self.period_start = user.get("period_start")
        self.period_end = user.get("period_end")
        self.embassy = Embassies[user.get("embassy")][0]
        self.facility = Embassies[user.get("embassy")][1]
        self.regex_continue = Embassies[user.get("embassy")][2]
        self.sign_in_link = (
            f"https://ais.usvisa-info.com/{self.embassy}/niv/users/sign_in"
        )
        self.appointment_url = f"https://ais.usvisa-info.com/{self.embassy}/niv/schedule/{self.schedule_id}/appointment"
        self.date_url = f"https://ais.usvisa-info.com/{self.embassy}/niv/schedule/{self.schedule_id}/appointment/days/{self.facility}.json?appointments[expedite]=false"
        self.time_url = f"https://ais.usvisa-info.com/{self.embassy}/niv/schedule/{self.schedule_id}/appointment/times/{self.facility}.json?date=%s&appointments[expedite]=false"
        self.sign_out_link = (
            f"https://ais.usvisa-info.com/{self.embassy}/niv/users/sign_out"
        )
        self.allow_rescheduling = True
        self.driver = None
        self.home_page = None

    def __str__(self):
        return (
            f"User({self.username})\n"
            f"Sign In Link: {self.sign_in_link}\n"
            f"Appointment URL: {self.appointment_url}\n"
            f"Date URL: {self.date_url}\n"
            f"Time URL: {self.time_url}\n"
            f"Sign Out Link: {self.sign_out_link}"
        )

    def get_valid_dates(self, dates):
        # Evaluation of different available dates
        def is_in_period(date, PSD, PED):
            new_date = datetime.strptime(date.get("date"), "%Y-%m-%d").date()
            # new_date = date.get("date")
            result = PED > new_date and new_date > PSD
            # print(f'{new_date.date()} : {result}', end=", ")
            return result

        # PED = datetime.strptime(self.period_end, "%Y-%m-%d")
        # PSD = datetime.strptime(self.period_start, "%Y-%m-%d")
        PED = self.period_end
        PSD = self.period_start

        avail_dates = [
            date.get("date")
            for date in dates
            if is_in_period(date, self.period_start, self.period_end)
        ]

        if not avail_dates:
            print(f"\n\nNo available dates between ({PSD}) and ({PED})!")

        return avail_dates

    def start_process(self):
        if not hasattr(self, "start_time"):
            self.start_time = datetime.now()

        if (
            self.driver
            and (datetime.now() - self.start_time).total_seconds()
            > SESSION_RESTART_TIME
        ):
            print(f"\n\nStopping process for {self.username}...")
            self.start_time = datetime.now()
            self.stop_process()
        elif self.driver:
            return

        print(f"\n\nStarting process for {self.username}...")
        self.driver = get_chrome_driver()

        self.driver.get(self.sign_in_link)
        time.sleep(STEP_TIME)
        Wait(self.driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
        auto_action(
            "Click bounce",
            "xpath",
            '//a[@class="down-arrow bounce"]',
            "click",
            "",
            STEP_TIME,
        )
        auto_action(
            self.driver, "Email", "id", "user_email", "send", self.username, STEP_TIME
        )
        auto_action(
            self.driver,
            "Password",
            "id",
            "user_password",
            "send",
            self.password,
            STEP_TIME,
        )
        auto_action(
            self.driver, "Privacy", "class", "icheckbox", "click", "", STEP_TIME
        )
        auto_action(
            self.driver, "Enter Panel", "name", "commit", "click", "", STEP_TIME
        )
        Wait(self.driver, 60).until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(text(), '" + self.regex_continue + "')]")
            )
        )

        self.driver.execute_script(f"window.open('{self.appointment_url}', '_blank');")
        time.sleep(3)

        self.home_page = self.driver.window_handles[0]
        self.appointment_page = self.driver.window_handles[1]

        print("\n\tlogin successful!\n")

    def stop_process(self):
        self.driver.get(self.sign_out_link)
        self.driver.quit()

    def reschedule(self, date):
        for time in reversed(self.get_times(date)):
            print("Trying to reschedule at %s %s" % (date, time))

            self.driver.switch_to.window(self.appointment_page)

            headers = {
                "User-Agent": self.driver.execute_script("return navigator.userAgent;"),
                "Referer": self.appointment_url,
                "Cookie": f"_gid={self.driver.get_cookie("_gid")["value"]}; _ga_CSLL4ZEK4L={self.driver.get_cookie("_ga_CSLL4ZEK4L")["value"]}; _ga={self.driver.get_cookie("_ga")["value"]}; _ga_W1JNKHTW0Y={self.driver.get_cookie("_ga_W1JNKHTW0Y")["value"]}; _yatri_session={self.driver.get_cookie("_yatri_session")["value"]}",
                "Origin": "https://ais.usvisa-info.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "upgrade-insecure-requests": "1",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "max-age=0",
                "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            }
            data = {
                "authenticity_token": self.driver.find_element(
                    by=By.NAME, value="authenticity_token"
                ).get_attribute("value"),
                "confirmed_limit_message": self.driver.find_element(
                    by=By.NAME, value="confirmed_limit_message"
                ).get_attribute("value"),
                "use_consulate_appointment_capacity": self.driver.find_element(
                    by=By.NAME, value="use_consulate_appointment_capacity"
                ).get_attribute("value"),
                "appointments[consulate_appointment][facility_id]": self.facility,
                "appointments[consulate_appointment][date]": date,
                "appointments[consulate_appointment][time]": time,
            }
            r = requests.post(self.appointment_url, headers=headers, data=data)

            if r.text.find("Successfully Scheduled") != -1:
                title = "SUCCESS"
                msg = f"Rescheduled Successfully! {date} {time}"
                self.allow_rescheduling = False
                self.driver.switch_to.window(self.home_page)

                return [title, msg]
            else:
                title = "FAIL"
                msg = f"Reschedule Failed!!! {date} {time}"

        self.driver.switch_to.window(self.home_page)
        return [title, msg]

    def get_times(self, date):
        time_url = self.time_url % date
        session = self.driver.get_cookie("_yatri_session")["value"]
        script = JS_SCRIPT % (str(time_url), session)
        content = self.driver.execute_script(script)
        data = json.loads(content)
        times = data.get("available_times")
        print(f"Got times successfully! {date} {times}")
        return times


def auto_action(driver, label, find_by, el_type, action, value, sleep_time=0):
    print("\t" + label + ":", end="")
    # Find Element By
    match find_by.lower():
        case "id":
            item = driver.find_element(By.ID, el_type)
        case "name":
            item = driver.find_element(By.NAME, el_type)
        case "class":
            item = driver.find_element(By.CLASS_NAME, el_type)
        case "xpath":
            item = driver.find_element(By.XPATH, el_type)
        case _:
            return 0
    # Do Action:
    match action.lower():
        case "send":
            item.send_keys(value)
        case "click":
            item.click()
        case _:
            return 0
    print("\t\tCheck!")
    if sleep_time:
        time.sleep(sleep_time)


def get_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


users = [User(user) for user in config["users"]]

avail_dates = []


def reschedule_check_all(users, all_dates):
    import concurrent.futures

    def process_user(user: User, all_dates):
        avail_dates = user.get_valid_dates(all_dates)
        result = []
        if not avail_dates:
            return result
        for date in avail_dates:
            user.driver.get(user.home_page)
            Wait(user.driver, 60).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(text(), '" + user.regex_continue + "')]")
                )
            )
            title, msg = user.reschedule(date)
            print(f"\t{title}: {msg}")
            result.append((title, msg))
            if title == "SUCCESS":
                return result
        return result

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_user, user, all_dates) for user in users]
        concurrent.futures.wait(futures)
        for future in futures:
            try:
                print(*future.result())
            except Exception as e:
                print(f"Exception occurred: {e}")
                traceback.print_exc()


def print_dates(all_dates):
    msg = ""
    for d in all_dates:
        msg = msg + "%s" % (d.get("date")) + ", "
    msg = "Available dates:\n" + msg if msg else "No available dates! \n"
    print(msg)


try:
    i = 0
    while True:
        user = users[i % len(users)]
        i += 1

        user.start_process()
        try:
            print(f"Getting dates for {user.username}...")
            print(f"Current time: {datetime.now().time()}")
            all_dates = json.loads(
                user.driver.execute_script(
                    JS_SCRIPT
                    % (user.date_url, user.driver.get_cookie("_yatri_session")["value"])
                )
            )

            print_dates(all_dates)

            if all_dates:
                reschedule_check_all(
                    [user for user in users if user.allow_rescheduling], all_dates
                )
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            user.stop_process()
            user.driver = None

        delay = 30 / (len(users))
        delay = random.uniform(delay, delay + 10)
        print(f"Delay: {delay}\n")
        time.sleep(delay)
except KeyboardInterrupt:
    print("Keyboard interrupt detected")
    for user in users:
        if user.driver:
            print(f"Stopping process for {user.username}...")
            user.driver.quit()
    sys.exit()
