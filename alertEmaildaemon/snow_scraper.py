import configparser
import requests
import re

file_name = r".conf"
conf_file = configparser.ConfigParser()
conf_file.read(file_name)

# need mail server - use gmail for now
username = str(conf_file.get("service_now", "username"))
password = str(conf_file.get("service_now", "password"))


class SNOW_Plow():
    """Class for retrieving Data from Service Now"""

    def __init__(self, username: str, password:str):
            
        self._username = username
        self._password = password


    def _parse_sitecode(self, sitecode: str) -> str:
        """Regularise site codes to match SNOW sitecodes by removing desciptive endings, adapted from existing perl script"""

        # split extension from naming convention to get core sitecode, remofves everythong after the first '_'
        query_sitecode = sitecode.split("_")[0]

        # using string.replace() as it's generally faster than regex
        
        # remove ending 'D' for 'SHPL' sites
        query_sitecode = (query_sitecode.replace("D", "") if "SHPL" in query_sitecode else query_sitecode)

        # remove Fortigate 'FGT' and 'ADS'
        query_sitecode = query_sitecode.replace("-FGT", "")
        query_sitecode = query_sitecode.replace("-ADS", "")

        # remove wruk -1
        query_sitecode = query_sitecode.replace("-1", "")

        query_sitecode = query_sitecode.replace("-CO-RTR", "")  
        query_sitecode = query_sitecode.replace("-CO-SWT", "")
        query_sitecode = query_sitecode.replace("-DO-RTR", "")
        query_sitecode = query_sitecode.replace("-DO-SWT", "")

        query_sitecode = query_sitecode.replace("_SEC", "")             # i think these are redundant
        query_sitecode = query_sitecode.replace("_DOPPLER", "")         # i think this is redundant

        return query_sitecode
    

    def _build_snow_sysparam_query(self, sitecode: str) -> str:
        """Takes a hns sitecode and generates a corresponding sysparam_query string for SNOW api"""
        
        # build sitecode section of query
        query_sitecode = self._parse_sitecode(sitecode)

        # special case for BPUK Fortigate sites
        if re.match("bpuk.*FGT", sitecode):
            query_sitecode = f"hns_u_sitecodeLIKE{query_sitecode}^hns_u_grade_of_serviceLIKEBT^ORhns_u_grade_of_serviceLIKECustomer^ORhns_u_grade_of_serviceLIKEFTTC^ORhns_u_grade_of_serviceLIKEADS"
        # special cases
        elif re.match("SLCZ.*DSL|SHPL.*DSL|SLHU.*DSL|SLSK.*DSL", sitecode):
            query_sitecode = f"hns_u_sitecodeLIKE{query_sitecode}^hns_sys_class_nameLIKEDSL^ORhns_sys_class_nameLIKEMWAVE^hns_u_stateLIKELive^hns_u_circuit_idISNOTEMPTY"
        # more special cases
        elif re.search("MGMT", sitecode):
            query_sitecode = f"hns_u_sitecodeLIKE{query_sitecode}^hns_u_stateLIKELive^hns_u_sim_imei_numberISNOTEMPTY"
        # even more special cases
        elif re.search("wruk", sitecode):
            query_sitecode = f"hns_u_sitecodeLIKE{query_sitecode}^hns_sys_class_nameLIKEDSL^ORhns_sys_class_nameLIKEVPN"
        else:
            query_sitecode = f"hns_u_sitecode={query_sitecode}"

        
        # build sysclass section of query
        # if any of DSL, RTR, WAN, CMD, SWR, BTAVS, or starts with EL
        if re.search("DSL|RTR|WAN|CMD|SWT|btavs", sitecode) or re.match("EL", sitecode):
            query_sysclass = "^hns_sys_class_nameLIKEDSL^ORhns_sys_class_nameLIKEMWAVE^ORhns_sys_class_nameLIKEPSTN^ORhns_sys_class_nameLIKECustomer"
        # Check for GPRS sites
        elif re.search("MGMT|\d{1}G|CMG|LTE", sitecode):
            query_sysclass = "^hns_sys_class_nameLIKEGPRS^ORhnsd_u_hybrid_technologyLIKEGPRS^hns_u_sim_imei_numberISNOTEMPTY^hns_u_stateLIKELive"
        else:
            query_sysclass = "^hns_sys_class_nameLIKEVSAT"

        return f"{query_sitecode}{query_sysclass}"


    def _parse_snow_response(self, sitecode:str, response:dict) -> dict:
        """Parse response from Service Now"""

        print(response)

        # unpack values from response, replace missing/not relevant with ""
        parsed = {
            "areacode": response.get("pre_u_area", ""),
            "postcode": response.get("prem_u_postcode", ""),
            "imei": response.get("hns_u_sim_imei_number", ""),
            "sim_provider": response.get("hns_u_sim_provider", ""),
            "grade": response.get("hns_u_grade_of_service", ""),
            "contract": response.get("hns_u_contract_number", ""),
            "contact_name": response.get("prem_u_contact_name", ""),
            "contact_number": response.get("prem_u_contact_number", ""),
            "circuit_id": response.get("hns_u_circuit_id", ""),
            "line_number": response.get("hns_u_line_number", ""),
            "conn_type": response.get("con_u_connection_type", ""),
            "conn_status": response.get("hns_u_state", ""),
            "snow_sitecode": response.get("hns_u_site_code", ""),
            "provider": response.get("hns_u_service_provider", "")
        }

        # create composite data fields
        print("!!!1")

        # for *_DSL_Remote and specified customer w/o DSL naming convention and connection type not starting with GPRS
        if (re.search("DSL|RTR|WAN|CMD|SWT|btavs", sitecode) or re.match("EL", sitecode)) and re.match("!GPRS", parsed["conn_type"]):
            print("!!!2")
            if re.search("UK|CMD", sitecode, re.IGNORECASE):
                parsed["service_desc"] = f"Line No: {parsed['line_number']}\BBEU:{parsed['circuit_id']}\nContract No:{parsed['contract']}\nGrade of Service:{parsed['grade']}"
            
            else:
                parsed["desc"] = f"Line No: {parsed['line_number']}\Circuit ID:{parsed['circuit_id']}\nContract No:{parsed['contract']}\nGrade of Service:{parsed['grade']}"
                # additional Information for DTAG Wholesale Portal	
                if re.search("DT\ -\ Wholesale", parsed["grade"], re.IGNORECASE):
                    if re.search("ADSL\ SA", parsed["grade"], re.IGNORECASE):
                        parsed["service_desc"] = f"{parsed['desc']}\nLeistungsnummer: 000303801"
                    elif re.search("ADSL\ SH", parsed["grade"], re.IGNORECASE):
                        parsed["service_desc"] = f"{parsed['desc']}\nLeistungsnummer: 000303802"
                    elif re.search("SDSL\ SA", parsed["grade"], re.IGNORECASE):
                        parsed["service_desc"] = f"{parsed['desc']}\nLeistungsnummer: 000303803"
                    elif re.search("VDSL\ SA", parsed["grade"], re.IGNORECASE):
                        parsed["service_desc"] = f"{parsed['desc']}\nLeistungsnummer: 000303804"

            # fix broken SN data (trailing ".0")
            parsed["postcode"] = parsed["postcode"].replace(".0", "")

            # determine if customer or HNS supplied
            parsed["supplied_by"] = "Customer" if re.search("Customer\sSupplied.*|BP\sEE", parsed["grade"]) else "HNS"
        
        # For mobile sites matching *anydigit*+G eg 3G / 4G / LTE
        elif re.search("MGMT|\d{1}G|CMG|LTE", sitecode):
            print("!!!3")

            # fix broken SN data (trailing ".0") on german sites only
            if re.search("DE", sitecode, re.IGNORECASE):
                parsed["postcode"] = parsed["postcode"].replace(".0", "")

            parsed["service_desc"] = f"SIM Provider: {parsed['sim_provider']}\nIMEI: {parsed['imei']}"

            # determine if customer or HNS supplied
            parsed["supplied_by"] = "Customer" if re.search("Customer\sSupplied.*|BP\sEE|EE", parsed['sim_provider']) else "HNS"
        
        # missing data
        else:
            parsed["service_desc"] = "Missing Data"
            parsed["supplied_by"] = "Missing Data"

        # merge contact info for sites of any type
        parsed["contact"] = f"Name: {parsed['contact_name']}\nNumber: {parsed['contact_number']}"

        return parsed

            
    def get_snow_data(self, sitecode: str, offset=0, limit=10000):
        """Retrieve Service Now data for passed site codes"""

        url = "https://hnseu.service-now.com/api/now/table/u_hns_sites_view__no_cpe_"
        paginate = False

        request_items =  ",".join([
            "prem_u_area",
            "prem_u_postcode",
            "hns_u_sim_imei_number",
            "hns_u_sim_provider",
            "hns_u_grade_of_service",
            "hns_u_contract_number",
            "prem_u_contact_name",
            "prem_u_contact_number",
            "hns_u_line_number",
            "hnsd_u_circuit_id",
            "hnsd_u_state",
            "hns_u_state",
            "con_u_connection_type",
            "hns_sys_class_name",
            "hns_u_circuit_id",
            "hns_u_site_code",
            "hns_u_service_provider",
            "hns_sys_id"
        ])

        params = {
            "sysparm_query": self._build_snow_sysparam_query(sitecode),
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
            "sysparm_suppress_pagination_header": "false" if paginate else "true",
            "sysparm_fields": request_items,
            "sysparm_offset": offset,
            "sysparm_limit": limit,
        }

        print(params["sysparm_query"])
        response = requests.get(url, auth=(self._username, self._password), params=params)
        print(response)
        # error handling for response
        data = response.json()["result"]

        # handle pagination
        if paginate:
            if int(response.headers["X-Total-Count"]) > offset + limit:
                data = data + self.get_snow_data(sitecode, offset + limit, limit)
        else:
            data = [data[0]]

        # parse response & generate combined fields
        parsed_data = [self._parse_snow_response(sitecode, row) for row in data]

        return parsed_data
    

    def get_snow_data_many(self, sitecodes: list):
        pass

print(username, password)
scraper = SNOW_Plow(username, password)
data = scraper.get_snow_data("bpuk12924-FGT_DSL_Remote", limit=10)
print(len(data))
print(data)