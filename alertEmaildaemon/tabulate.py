#! /usr/bin/env/ python
# Class for rendering 2-D Lists as HTML tables and pretty-print text
# Author: Milo Bashford

class Tabulator():
    
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

        table = """<table>"""
    
        # create table header
        table += "<tr>"
        for col in self._columns:
            table += f"<th>{col}</th>"
        table += "</tr>"

        # create table rows
        for row in self._rows:
            table += "<tr>"
            for val in row:
                table += f"<td>{val}</td>"
            table += "</tr>"

        # create table footer
        table += "</table>"

        return table