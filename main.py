from pymongo import MongoClient, InsertOne
from selenium import webdriver
import time
from bs4 import BeautifulSoup
import requests
import re


class Parser:
    def __init__(self, cred_email, cred_password):
        self.url = 'https://rabota.ua/'
        self.driver = webdriver.Chrome(executable_path="/home/user/PycharmProjects/test01/ad-masters-task/chromedriver")
        self.cred_email = cred_email
        self.cred_password = cred_password
        self.vacans_url = 'https://notebook.rabota.ua/employer/notepad/cvs?vacansyId=-1'
        self.client = MongoClient('mongodb://localhost')
        self.db = self.client['test_db']
        self.collection = self.db['test_coll']

    def login(self):
        self.driver.get(self.url)
        log_in_button = self.driver.find_element_by_xpath('//*[@id="ctl00_Header_header"]/div/header/div/div/ul/li[4]/a[1]/label')
        log_in_button.click()
        email_raw = self.driver.find_element_by_xpath('//*[@id="ctl00_Sidebar_login_txbLogin"]')
        password_raw = self.driver.find_element_by_xpath('//*[@id="ctl00_Sidebar_login_txbPassword"]')
        email_raw.send_keys(self.cred_email)
        password_raw.send_keys(self.cred_password)
        login_button = self.driver.find_element_by_xpath('//*[@id="ctl00_Sidebar_login_lnkLogin"]')
        login_button.click()
        time.sleep(1)

    def get_all_elements_from_xpath(self, xpath, count=1):
        all_items = []
        while True:
            try:
                all_items.append(self.driver.find_element_by_xpath(xpath.format(count)))
                count += 1
            except:
                break
        return all_items

    def save_to_directory(self, text, path):
        file = open(path, 'w')
        file.write(text)
        file.close()

    def get_additional_info(self, url):
        self.driver.get(url)
        html = self.driver.find_element_by_xpath('/html')
        soup = BeautifulSoup(html.get_attribute('innerHTML'), 'lxml')
        data = {}
        try:
            data['email'] = soup.find('span', id='ctl00_centerZone_BriefResume1_CvView1_cvHeader_lblEmailValue').text
        except:
            try:
                data['email'] = soup.find('span', id='ctl00_centerZone_BriefResume1_ViewAttachedCV1_cvHeader_lblEmailValue').text
            except:
                data['email'] = None
        try:
            data['phone_number'] = soup.find('span', id='ctl00_centerZone_BriefResume1_CvView1_cvHeader_lblPhoneValue').text
        except:
            data['phone_number'] = None
        try:
            data['socials'] = [item['href'] for item in soup.find('span', id='ctl00_centerZone_BriefResume1_CvView1_cvHeader_lblSocNetworkValue').find_all('a')]
        except:
            data['socials'] = None
        try:
            data['city'] = soup.find('span', id='ctl00_centerZone_BriefResume1_CvView1_cvHeader_lblRegionValue').text
        except:
            data['city'] = None
        cv_url = soup.find('', text='Скачать').parent['href']
        cv_response = requests.get(cv_url)
        try:
            # cv data only for logged users
            file_name = re.search('".*"', cv_response.headers['Content-Disposition'].split(';')[1]).group(0).replace('"', '')
            cv_file_path = '/home/user/PycharmProjects/test01/ad-masters-task/files_storage/{}'.format(file_name)
            self.save_to_directory(cv_response.text, cv_file_path)
            data['cv_file_path'] = cv_file_path
        except:
            data['cv_file_path'] = None
        return data

    def parse_vacans(self, html):
        data = {}
        soup = BeautifulSoup(html, 'lxml')
        full_name_splited = soup.find('a', class_='rua-p-t_16 rua-p-c-default ga_cv_view_cv').text.split(' ')
        data['person_url'] = soup.find('a', class_='rua-p-t_16 rua-p-c-default ga_cv_view_cv')['href']
        if full_name_splited.__len__() == 2:
            data['name'] = full_name_splited[0]
            data['surname'] = full_name_splited[1]
        else:
            data['name'] = full_name_splited[1]
            data['surname'] = full_name_splited[0]
        additional_data = self.get_additional_info(data['person_url'])
        data.update(additional_data)
        self.driver.back()
        return data

    def parse_table_vacans(self, vacans_name):
        inner_table_vacancies = [item.get_attribute('innerHTML') for item in self.get_all_elements_from_xpath('//*[@id="ctl00_centerZone_employerResumeList_grVwResume"]/tbody/tr[{}]', 2)]
        parsed_table_vacans = list(map(self.parse_vacans, inner_table_vacancies))
        [vacans.update({'vacans_name':vacans_name}) for vacans in parsed_table_vacans]
        return parsed_table_vacans

    def parse_all_vacans(self):
        self.driver.get(self.vacans_url)
        resume = self.driver.find_element_by_xpath('//*[@id="ctl00_centerZone_employerResumeList_pnlWrapper"]/div[1]/div[1]/div/span/span[1]/span')
        resume.click()
        all_vacans = self.get_all_elements_from_xpath('//*[@id="select2-ddlVacancyFilter-results"]/li[3]/ul/li[{}]')
        for count, vacans in enumerate(all_vacans):
            try:
                vacans = update_vacans[count]
            except:
                pass
            vacans_name = vacans.text.split(',')[0]
            vacans.click()
            parsed_vacansies = self.parse_table_vacans(vacans_name)
            self.driver.back()
            time.sleep(2)
            resume = self.driver.find_element_by_xpath(
                '//*[@id="ctl00_centerZone_employerResumeList_pnlWrapper"]/div[1]/div[1]/div/span/span[1]/span')
            resume.click()
            update_vacans = self.get_all_elements_from_xpath('//*[@id="select2-ddlVacancyFilter-results"]/li[3]/ul/li[{}]')
            docs = [InsertOne(item) for item in parsed_vacansies]
            if docs:
                self.collection.bulk_write(docs)


instant = Parser(cred_email='oksana@theadmasters.com',
                 cred_password='Q2eV6uVXgge4Ze5')
instant.login()
instant.parse_all_vacans()

