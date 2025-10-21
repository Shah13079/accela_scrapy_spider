import scrapy
from scrapy.http import FormRequest
from utilities import license_pro_info

class MissoulaPermitSpider(scrapy.Spider):
    name = "miss_spider"
    allowed_domains = ["aca-prod.accela.com"]

    ALL_FIELDS = [
        'page', 'listing_detail_url', 'date', 'permit_number', 'permit_type', 
        'description', 'address', 'status', 'work_location', 
        'license_pro_business_name', 'license_pro_address_line', 'license_pro_city',
        'license_pro_state', 'license_pro_zip', 'license_pro_business_license',
        'license_pro_po_box', 'license_pro_phone_num_1', 'license_pro_phone_num_2',
        'license_pro_phone_num_3'
    ]
    
    start_url= "https://aca-prod.accela.com/MISSOULA/Cap/CapHome.aspx?module=Building&TabName=Building&TabList=Home%7c0%7cBuilding%7c1%7cFire%7c2%7cEngineering%7c3%7cLicenses%7c4%7cPlanning%7c5%7cCurrentTabIndex%7c1"
   
    def _get_headers(self, response_url):
            """Create a dynamic header."""
            return {
                "Origin": "https://aca-prod.accela.com",
                "Referer": response_url, 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
            }
    
    def start_requests(self):
    
        yield scrapy.Request(url=self.start_url, callback=self.parse_initial)


    def parse_initial(self, response):
        form_data = {}
        for input_field in response.xpath('//input'):
            name = input_field.xpath('./@name').get()
            value = input_field.xpath('./@value').get()
            if name:
                form_data[name] = value if value is not None else ''
        
        form_data.update({
            "__EVENTTARGET": "ctl00$PlaceHolderMain$btnNewSearch",
            "ctl00$PlaceHolderMain$generalSearchForm$txtGSStartDate": "11/17/1764",
            "ctl00$PlaceHolderMain$generalSearchForm$txtGSEndDate": "10/20/2025",
            'ctl00$PlaceHolderMain$dgvPermitList$ddlPageSize': '5',
        })


        yield FormRequest(
            url=response.url,
            formdata=form_data,
            headers= self._get_headers(response.url),
            callback=self.parse_results,
            dont_filter=True
        )
    
    def parse_results(self, response):
        current_page = response.xpath('//span[@class="SelectedPageButton font11px"]/text()').get(default='1')
        self.logger.info(f"Scraping Page Number: {current_page}")

        permit_rows = response.xpath(
            '//table[contains(@id, "gdvPermitList")]//tr[contains(@class, "ACA_TabRow_Odd") or contains(@class, "ACA_TabRow_Even")]'
        )
        
        for row in permit_rows:
            full_item = {key: '' for key in self.ALL_FIELDS}
            relative_url = row.xpath('.//td[3]//a/@href').get()
            detail_url = response.urljoin(relative_url) if relative_url else ''

            permit_basic_info = {
                'page': current_page,
                'listing_detail_url': detail_url,
                'date': row.xpath('string(.//td[2])').get(default='').strip(),
                'permit_number': row.xpath('string(.//td[3])').get(default='').strip(),
                'permit_type': row.xpath('string(.//td[4])').get(default='').strip(),
                'description': row.xpath('string(.//td[5])').get(default='').strip(),
                'address': row.xpath('string(.//td[6])').get(default='').strip(),
                'status': row.xpath('string(.//td[7])').get(default='').strip(),
            }
            
            full_item.update(permit_basic_info)

            # Only sent detail request if we found a valid detail URL. 
            # Otherwise just yield the basic data we have scraped from listings page.
            
            if detail_url:
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    meta={'permit_data': permit_basic_info}
                )
            else:
                yield full_item
                
        next_page_link = response.xpath('//a[text()="Next >"]')
        if next_page_link:
            self.logger.info("Next page link found, preparing request...")

            form_data = {}
            for input_field in response.xpath('//input'):
                name = input_field.xpath('./@name').get()
                value = input_field.xpath('./@value').get()
                if name:
                    form_data[name] = value if value is not None else ''

            form_data.update({
                '__EVENTTARGET': 'ctl00$PlaceHolderMain$dgvPermitList$gdvPermitList',
                '__EVENTARGUMENT': 'Page$Next'
            })
            
           
            yield FormRequest(
                url=response.url,
                formdata=form_data,
                headers= self._get_headers(response.url),
                callback=self.parse_results,
                dont_filter=True
            )
        
    def parse_detail(self, response):
        item = response.meta['permit_data']

        # Work Location
        work_location_raw = response.xpath('string(//table[@id="tbl_worklocation"]//span[@class="fontbold"])').get()
        work_location = work_location_raw.strip() if work_location_raw else None
        item['work_location'] = work_location

        #if license professional section available
        license_professional_row = response.xpath('//td[.//h1/span[contains(text(), "Licensed Professional:")]]')
        if license_professional_row:
            # Get the HTML of the row already found
            raw_sec_html = license_professional_row.get()
            if raw_sec_html:
                license_p_info = license_pro_info(raw_sec_html)
                item.update(license_p_info)

        yield item
        
        