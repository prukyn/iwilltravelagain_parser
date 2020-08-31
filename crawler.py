import requests
import bs4
import time
import csv

import cfscrape

from multiprocessing import Pool, Manager
from functools import partial


class PageObject:

    def get_page(self, url:str, format: str= 'text', **kwargs):
        scraper = cfscrape.create_scraper()
        resp = scraper.get(url, **kwargs)
        if format == 'text':
            return resp.text
        if format == 'json':
            return resp.json()
    
    def parse_attr_by_css_selector(self, page:str, locator: str, attr:str = None):
        soup = bs4.BeautifulSoup(page, 'lxml')
        elements = soup.select(locator)
        if attr is not None:
            items = [ item[attr] for item in elements]
            return items
        else:
            items = [ item.text.strip() for item in elements]
            return items
    
    def save_to_csv(self, filename:str, data: tuple):
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(data)


class IWillTravelAgainLocators:
    
    REGION_LOCATOR = 'a.link.a-image-button'
    REGION_NAME_LOCATOR = 'div.inner.prose > h4'
    POST_ID_LOCATOR = '#activity-grid-1'
    POST_ID_ATTR = 'data-post-id'
    COMPANY_WEBSITE_LOCATOR = 'div.button-block:nth-child(2) > a:nth-child(1)'


class IWillTravelAgainParser(PageObject):
    
    def __init__(self, url:str, api_url:str):
        self.URL = url
        self.API = api_url
        self.locators = IWillTravelAgainLocators()     

    def parse_regions_on_main_page(self):
        page = self.get_page(self.URL)
        regions = self.parse_attr_by_css_selector(page, self.locators.REGION_NAME_LOCATOR)
        links = self.parse_attr_by_css_selector(page, self.locators.REGION_LOCATOR, 'href')
        return tuple(zip(regions, links))
    
    def parse_region_page_params(self, link: str):
        page = self.get_page(link, params={'page': 1})
        post_id = self.parse_attr_by_css_selector(page, self.locators.POST_ID_LOCATOR, self.locators.POST_ID_ATTR)
        return post_id

    def get_all_companies_on_page(self, url:str, post_id:str):
        api = self.get_page(url, format='json', params={'post_id': post_id, 'key': 'rows_2_grid_activities'})
        return api

    def get_company_data(self, company: dict, region:str):
        title = company.get('title')
        try:
            category = company['taxonomies'].get('activity_category').get('termString')
        except AttributeError:
            category = ''

        location = self.get_location(company['taxonomies'])
        link = company.get('link')
        try:
            website = self.get_website(self.URL+link)
            data = tuple([region, title, category, location, website])
            return data
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError, requests.exceptions.ReadTimeout, IndexError):
            return company

    def get_location(self, item: dict):
        loc = item.get('location')
        if loc is not None:
            loc = loc.get('termString', '')
        return loc
        
    def get_website(self, link, **kwargs):
        page = self.get_page(link, timeout=None, **kwargs)
        try:
            website = self.parse_attr_by_css_selector(page, self.locators.COMPANY_WEBSITE_LOCATOR, 'href')[0]
        except IndexError:
            website = ''
        return website

    def parse_region(self, region_data: tuple):
        region, link = region_data
        post_id = self.parse_region_page_params(link)
        companies = self.get_all_companies_on_page(self.API, post_id)
        with Manager() as manager:
            success_list = manager.list()
            with Pool(15) as p:
                get_company_data_ = partial(self.get_company_data, region=region)
                for result in p.imap_unordered(get_company_data_, companies, 15):
                    if isinstance(result, tuple):
                        print(result)
                        success_list.append(result)
                    else:
                        res_again = None
                        while not isinstance(res_again, tuple):
                            print('try again', result)
                            res_again = self.get_company_data(result, region)
                        success_list.append(res_again)
                        
            self.save_to_csv('data.csv', success_list)

    def parse(self):
        regions = self.parse_regions_on_main_page()
        for region in regions:
            print(regions)
            self.parse_region(region)

def main():
    URL = 'https://iwilltravelagain.com'
    API_URL = 'https://iwilltravelagain.com/wp-json/FH/activities'
    
    start = time.time()
    parser = IWillTravelAgainParser(URL, API_URL)
    parser.parse()

    end = time.time()
    print(f'total: {end - start}')

if __name__ == "__main__":
    main()
