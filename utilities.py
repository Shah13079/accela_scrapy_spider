from scrapy.selector import Selector
import re

def extract_business_license(line):
    """
    Extract the license code from lines starting with any uppercase label,
    e.g. "CONTRACTOR 2015-MSS-CON-00062" or "LICENSE 1234-XYZ".
    Returns the code string only, or '' if no match.
    """
    pattern = re.compile(r'^([A-Z]+)\s+([\w\-]+)', re.IGNORECASE)
    match = pattern.match(line.strip())
    if match:
        return match.group(2)
    return ''

async def safe_element_exists(page, xpath):
    try:
        return await page.locator(xpath).count() > 0
    except:
        return False

async def safe_get_html(page, xpath):
    try:
        element = page.locator(xpath).first
        if await element.count() > 0:
            return await element.inner_html()
    except:
        pass
    return ""

def extract_po_box(line):
    """
    Detects if the line is a PO BOX address.
    Returns the PO BOX string (e.g., "PO BOX 1951") if matched, else ''.
    """
    po_box_pattern = r'\b(?:P\.?\s*O\.?|POST\s+OFFICE)\s+BOX\s+\d+(?:-\d+)?\b'
    
    match = re.search(po_box_pattern, line, re.IGNORECASE)
    return match.group(0) if match else ''


#HELPER FUNCTIONS FOR PARSING Permit DETAILS 
def is_address_line(line):
    street_suffixes = [
        "ST", "AVE", "AVENUE", "BLVD", "RD", "ROAD", "DR", "DRIVE", "CT", "LN", "LANE", 
        "PKWY", "PL", "WAY", "HWY", "TERR", "EXPRESSWAY", "TRAIL", "CIR", "LOOP",
        "E.", "W.", "N.", "S.", "SUITE", "STE", "UNIT", "FLOOR", "APT"
    ]
    suffix_pattern = re.compile(r'\b(' + '|'.join(street_suffixes) + r')\b', re.IGNORECASE)
    
    # Use word boundaries to check for whole words only
    exclude_pattern = re.compile(r'\b(phone|contractor|mt|id|zip|fax|wa|nd|sd)\b', re.IGNORECASE)

    stripped = line.strip()

    if exclude_pattern.search(stripped.lower()):
        return ''
    # Include if line has address suffix keyword and at least one digit
    if suffix_pattern.search(stripped) and re.search(r'\d', stripped):
        return stripped

    return ''


def extract_city_state_zip(line):
    """
    Extract city, state, and zip (if any) from a single line.
    Returns dict with keys if found, else empty string for missing parts.
    Returns empty dict if no match.
    """

    line = line.strip()
    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL',
        'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT',
        'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
        'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]
    states_regex = '|'.join(states)
    # Regex to capture city, state, zip (zip optional)
    # Accept commas or spaces as separators
    pattern = re.compile(
        rf"""
        ^\s*
        (?P<city>[\w\s\.\'\-]+?)    # city - lazy match, words/spaces/dots/quotes/hyphens
        [, ]+                       # separator (comma or space, one or more)
        (?P<state>{states_regex})   # state abbreviation
        (?:[, ]+\s*(?P<zip>\d{{5}}(?:-\d{{4}})?))?  # optional zip code with optional +4
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    match = pattern.match(line)
    if not match:
        return {}

    city = match.group('city').strip()
    state = match.group('state').upper()
    zip_code = match.group('zip') or ''

    return {
        'license_pro_city': city,
        'license_pro_state': state,
        'license_pro_zip': zip_code
    }



def license_pro_info(html_content):
    # Create a selector object from the raw HTML string
    html_content = Selector(text=html_content)
    
 
    # This now specifically targets the second <td> inside the correct table
    professional_text_details = html_content.xpath(
        '//table[@id="tbl_licensedps"]//tr/td[2]//text()[not(ancestor::table[@class="ACA_TDAlignLeftOrRightTop"])]'
    ).getall()

    # Clean up the extracted text lines
    professional_details = [
        item.strip() for item in professional_text_details 
        if item.strip() and item.strip() != '*' and 'Phone' not in item
    ]
    
    filtered = [
        s for s in professional_details
        if not re.match(r'^BL\d+$', s.strip())
    ]
    
    # Initialize the dictionary to store results
    license_p_details = {
        'license_pro_business_name': '',
        'license_pro_address_line': '',
        'license_pro_city': '',
        'license_pro_state': '',
        'license_pro_zip': '',
        'license_pro_business_license': '',
        'license_pro_po_box': '',
        'license_pro_phone_num_1': '',
        'license_pro_phone_num_2': '',
        'license_pro_phone_num_3': ''
    }


    # Moved this outside the loop to run only once
    phone_numbers = html_content.xpath('//div[@class="ACA_PhoneNumberLTR"]/text()').getall()
    clean_phones = (item.strip() for item in phone_numbers if item.strip())
    for ind, each_num in enumerate(clean_phones, start=1):
        if f"license_pro_phone_num_{ind}" in license_p_details:
            license_p_details[f"license_pro_phone_num_{ind}"] = each_num

    # Loop through the filtered text lines to categorize them
    for idx, each_line in enumerate(filtered, start=1):
        if idx == 1:
            license_p_details['license_pro_business_name'] = each_line
            continue

        po_box = extract_po_box(each_line)
        if po_box:
            license_p_details['license_pro_po_box'] = po_box
            continue

        address_line = is_address_line(each_line)
        if address_line:
            license_p_details['license_pro_address_line'] = address_line
            continue
        
        city_state_zip = extract_city_state_zip(each_line)
        if city_state_zip:
            license_p_details.update(city_state_zip)
            continue

        license_code = extract_business_license(each_line)
        if license_code:
            license_p_details['license_pro_business_license'] = license_code
            continue
    
    return license_p_details