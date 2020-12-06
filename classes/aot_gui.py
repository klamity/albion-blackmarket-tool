from tkinter import (
    Scrollbar,
    Canvas,
    StringVar,
    Tk,
    RIGHT,
    Y,
    Frame,
    LEFT,
    BOTH,
    NW,
    W,
    OptionMenu,
    Button,
    Label,
    PhotoImage
)

from datetime import datetime

from id_to_name import id_to_name

from datainfo import (
    city_list, file_list, client_version, client_title, quality_list
)

import requests

data_route = 'https://www.albion-online-data.com/api/v2/stats/prices/'
tax = 0.06

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

flatten = lambda t: [item for sublist in t for item in sublist]

def item_requests(items, city):
    item_list = list(chunks(items, 190))
    city_queries = []
    bm_queries = []
    for query in item_list:
        q = ''
        if query == item_list[-1]:
            q = ','.join(query)[:-1]
        else:
            q = ','.join(query)
        city_queries.append(requests.get(data_route + q + '?locations=' + city).json())
        bm_queries.append(requests.get(data_route + q + '?locations=blackmarket').json())

    return (flatten(city_queries), flatten(bm_queries))

class AOTGui:
    def __init__(self):
        self.gui =  Tk()
        self.gui.title(client_title)
        self.gui.geometry('800x500')
        self.numRow = 0
        scrollbar = Scrollbar(self.gui)
        self.canvas = Canvas(self.gui, bg='pink', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.frame = Frame(self.canvas)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.canvas.create_window(0, 0, window=self.frame, anchor=NW)
        self.var_city = StringVar(self.frame)
        self.var_file = StringVar(self.frame)
        self.var_city.set(city_list[0])
        self.var_file.set(file_list[0])

        Label(self.frame, text='Version '+str(client_version), bg='turquoise').grid(row=0, column=0)

        Label(self.frame, text='City').grid(row=1, column=0, sticky=W)
        OptionMenu(self.frame, self.var_city, *city_list).grid(row=1, column=1, sticky=W)
        Label(self.frame, text='Items', padx=15).grid(row=1, column=2, sticky=W)
        OptionMenu(self.frame, self.var_file, *file_list).grid(row=1, column=3, sticky=W)
        Button(self.frame, text='Search', command=self.cmd_search).grid(row=1, column=4, sticky=W)

        Label(self.frame, text='Item').grid(row=2, column=0, columnspan=2, sticky=W)
        Label(self.frame, text='Price', padx=15).grid(row=2, column=2, sticky=W)
        Label(self.frame, text='Black Market', padx=15).grid(row=2, column=3, sticky=W)
        Label(self.frame, text='Profit', padx=15).grid(row=2, column=4, sticky=W)

        self.gui.update()
        self.canvas.config(scrollregion=self.canvas.bbox('all'))
        self.gui.mainloop()

    def human_readable_value(self,value):
        if 1e3 <= value < 1e6:
            return str(round(value/1e3)) + ' k'
        elif 1e6 <= value:
            return str(round(value/1e6, 1)) + ' m'
        else:
            return str(value)

    def add_item(self, item_id, name, price, blackmarket, profit):
        img = PhotoImage(file='img/'+item_id+'.png')
        label = Label(self.frame, image=img)
        label.image = img
        label.grid(row=3+self.numRow, column=0, sticky=W)
        Label(self.frame, text=name).grid(row=3+self.numRow, column=1, sticky=W)
        Label(self.frame, text=self.human_readable_value(price), padx=15).grid(row=3+self.numRow, column=2, sticky=W)
        Label(self.frame, text=self.human_readable_value(blackmarket), padx=15).grid(row=3+self.numRow, column=3, sticky=W)
        Label(self.frame, text=self.human_readable_value(profit), padx=15).grid(row=3+self.numRow, column=4, sticky=W)
        self.numRow += 1
        self.gui.update()
        self.canvas.config(scrollregion=self.canvas.bbox('all'))

    def reset(self):
        self.numRow = 0
        for widget in self.frame.winfo_children()[10:]:
            widget.destroy()
        self.frame.pack_forget()

    def cmd_search(self):
        self.reset()
        city = self.var_city.get() 
        item_file = 'items/' + self.var_file.get()
        item_query = open(item_file, 'r').read().replace('\n', ',')[:-1]
        item_array = open(item_file, 'r').read().split('\n')
        r = item_requests(item_array, city)
        if not item_query:
            return
        response_city= r[0]
        response_blackmarket = r[1]
        #    response_city = requests.get(data_route + item_query + '?locations=' + city).json()
        #    response_blackmarket = requests.get(data_route + item_query + '?locations=blackmarket').json()
        offer_dict = {}
        for entry in response_city:
            item = entry['item_id']
            value = entry['sell_price_min']
            quality = entry['quality']
            name = item + "#" + str(quality)

            if value:
                offer_dict[name] = [value, 0]

        for entry in response_blackmarket:
            item = entry['item_id']
            value = entry['buy_price_max']
            time = entry['sell_price_min_date']
            a = datetime.now() - datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
            qualities = [x for x in range(entry['quality'], 6)]
            items_to_purchase = [item+"#"+str(x) for x in qualities]
            city_values = []
            for item_key in items_to_purchase:
                if item_key in offer_dict.keys():
                    item_city_value = offer_dict[item_key][0]
                    city_values.append(item_city_value)
            if len(city_values) > 0:
                offer_dict[items_to_purchase[0]] = [min(city_values), value, a]
        full_list = sorted(offer_dict.items(), key=lambda x:(x[0], -x[1][1]+x[1][0], time))
        profit_list = []

        for item in full_list:
            name = item[0]
            values_pair = item[1]
            time = values_pair[2]
            profit = round(values_pair[1]*(1-tax) - values_pair[0])
            if profit > 0 and (1 - values_pair[0] / profit) < 0.85:
                profit_list.append([name, values_pair, profit, time])

        profit_list.sort(key=lambda x:(x[2]))

        i = 0
        for item in profit_list[::-1]:
            _id, _quality = item[0].split('#')

            enchant = item[0][-3] if "@" in item[0] else '0'
            tier = _id[1]
            quality = quality_list[int(_quality) -1]
            if _id in id_to_name.keys():
                translated_name = id_to_name[_id]
            else:
                tier = ''
                enchant = ''
                translated_name = _id

            name = f'{tier}.{enchant} {translated_name}, {quality}'

            item_id = item[0].split('#')[0]
            price = item[1][0]
            blackmarket = item[1][1]
            profit = item[2]
            time = item [3]

            self.add_item(item_id, name, price, blackmarket, profit)
            i += 1






