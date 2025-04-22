#! /usr/bin/env python
# Author: Milo Bashford

import configparser
import smtplib
import ssl

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

file_name = r".conf"
conf_file = configparser.ConfigParser()
conf_file.read(file_name)

# need mail server - use gmail for now
smtp_host_adr = str(conf_file.get("smtp_server", "host_addr"))
smtp_host_prt = str(conf_file.get("smtp_server", "host_port"))
smtp_username = str(conf_file.get("smtp_server", "username"))
smtp_password = str(conf_file.get("smtp_server", "password"))

# get sender
email_orig = str(conf_file.get("email_options", "orig"))


class Tabulator():
    """Class for rendering 2-D Lists as HTML tables and pretty-print text"""

    def __init__(self, data: list, table_padding=0, value_padding=1):

        if len(data) <1:
            raise Exception("passed data must contain at aleast one record")
        
        if type(data[0]) in [list, tuple]:
            self._columns = data[0]
            self._rows = data[1:]

        elif type(data[0]) == dict:         # restructure rowdata as 2d array
            self._columns = list(data[0].keys())
            self._rows = [[row[col] for col in self._columns] for row in data]

        else:
             raise TypeError("Passed data must be structured as a 2D array or a list of dictionaries")
        
        self._table_padding = table_padding
        self._value_padding = value_padding

        self._col_widths = self._get_longest_strings()
        self._table_width = sum(self._col_widths) + (len(self._columns) * (1 + (self._value_padding * 2))) + 1
        

    def _get_longest_strings(self) -> list:
        
        char_lens = []
        for i in range(0, len(self._columns)):
            s_lens = [len(self._columns[i])] + [len(row[i]) for row in self._rows]
            char_lens.append(max(s_lens))

        return char_lens
        
        
    def tabulate_as_str(self) -> str:
        
        t = self._table_padding
        v = self._value_padding 

        table = """"""

        # create table header
        table += f"{' ' * t}{'=' * self._table_width}\n"

        cols = [self._columns[i].ljust(self._col_widths[i]) for i in range(len(self._columns))]
        table += f"{' ' * t}|{' ' * v}" + f"{' ' * v}|{' ' * v}".join(cols) + f"{' ' * v}|\n"
        table += f"{' ' * t}{'=' * self._table_width}\n"

        # create table rows
        for row in self._rows:
            r = [row[i].ljust(self._col_widths[i]) for i in range(len(self._columns))]
            table += f"{' ' * t}|{' ' * v}" + f"{' ' * v}|{' ' * v}".join(r) + f"{' ' * v}|\n"

        # create table footer
        table += f"{' ' * t}{'=' * self._table_width}\n"

        return table
    
    
    def tabulate_as_html(self):

        header_fill = "#992846"
        row_fill = "#e8e1e3"

        table = """<table style="width:450px;margin:0;" cellpadding="0" cellspacing="0" border="1px">"""
    
        # create table header
        table += f"""<tr style="background-color:{header_fill}; height:40px; width:450px; margin:0; color:white">"""
        for col in self._columns:
            table += f"""<th>{col}</th>"""
        table += "</tr>"

        # create table rows
        i = 0
        for row in self._rows:
            table += f"""<tr style="background-color:{row_fill if i % 2 == 1 else "white"}; height:40px; width:10px; margin:0;">"""
            for val in row:
                table += f"<td>{val}</td>"
            table += "</tr>"
            i += 1

        # create table footer
        table += "</table>"

        return table


class HNS_Emailer():
    """Handles sending alert emails via external SMTP server"""

    def __init__(self, host_addr, host_port, username, password, origin):

        self._host_addr = host_addr
        self._host_port = host_port
        self._username = username
        self._password = password
        self._origin = origin


    def _build_email(self, data, subject:str, dest: list):

        tabulator = Tabulator(data, table_padding=4)
        
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self._origin
        msg["To"] = ",".join(dest)

        # create plaintext message
        text = f"""Alert\n\n{tabulator.tabulate_as_str()}
        """

        # create html message
        html = f"""\
            <html>
                <body>
                    <p>
                    Alert
                    {tabulator.tabulate_as_html()}
                    </p>
                </body>
            </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        return msg


    def send_email(self, data, subject, dest):

        ctx = ssl.create_default_context()

        msg = self._build_email(data, subject=subject, dest=dest)

        with smtplib.SMTP_SSL(self._host_addr, self._host_port, context=ctx) as server:
            server.login(self._username, self._password)
            server.sendmail(self._username, dest, msg.as_string())


# send test email

data = [
    ["City", "Time", "Amount"],
    ["Dublin", "12:00", "50"],
    ["Berlin", "13:00", "2000"]
]

mailer = HNS_Emailer(smtp_host_adr, smtp_host_prt, smtp_username, smtp_password, email_orig)
mailer.send_email(data, "Alert!", ["milobashford@gmail.com", "m.bashford@hugheseurope.com"])

