from __future__ import print_function
import configparser
import json
import os
import requests
import json_to_csv
import sys
import pandas as pd


def get_sort_value(sort, fields):
    sort_fields, sort_directions = [], []
    for dct in sort:
        for field in dct:
            # 只能依照指定欄位排序
            if field in fields:
                sort_fields.append(field)
                sort_directions.append(dct[field])
    if len(sort_fields) == 0:
        sort_fields = [fields[0]]
        sort_directions = ["asc"]
    
    return [sort_fields, sort_directions]


def get_config_value(parser, n):
    section = parser.sections()[n]

    entity = json.loads(parser.get(section, 'entity'))
    url = 'https://www.patentsview.org/api/'+entity+'/query?'
    input_file = json.loads(parser.get(section, 'input_file'))
    directory = json.loads(parser.get(section, 'directory'))
    input_type = json.loads(parser.get(section, 'input_type'))
    fields = json.loads(parser.get(section, 'fields'))
    sort = json.loads(parser.get(section, 'sort'))
    sorts = get_sort_value(sort, fields)

    # 取得有criteria開頭的參數加入
    criterias = {"_and": [json.loads(parser.get(section, option)) for option in
                    parser.options(section) if option.startswith('criteria')]}

    return [url, entity, input_file, directory, input_type, fields, sorts, criterias]

def check_res_status(res, item):
    if 400 <= res.status_code <= 499:
        print("Client error when quering for value {}".format(item))
        return False
    elif res.status_code >= 500:
        print("Server error when quering for value {}. You may be exceeding the maximum API request size (1GB).".format(item))
        return False
    else:
        return True



def query_one_patent(item, patent_values, results_found):
    n = results_found
    per_page = 10000
    count = per_page
    page = 1
    while count == per_page:
        count = 0
        params = {
        'q': {"_and": [{patent_values[4]: item}, patent_values[7]]},
        'f': patent_values[5],
        'o': {"per_page": per_page, "page": page}
        }

        res = requests.post(patent_values[0], data=json.dumps(params))
        patent_data =  json.loads(res.text)

        print('---------------------------------')
        print(patent_data)
        print('---------------------------------')
        page += 1

        # 檢查網路狀態
        status = check_res_status(res, item)
        if(status):
            count = patent_data['count']
            if(count != 0):
                # 產生json來供之後產生csv
                outp = open(os.path.join(patent_values[3], 'Patent' + '_' + str(n) + '.json'), 'w')
                print(res.text, end = '', file=outp)
                outp.close()
                n += 1
    return n


def query():

    patent_values = [] # patent 設定檔參數
    item_list = [] # 需要搜尋的id list
    results_found = 0

    # 搜尋設定檔
    parser = configparser.ConfigParser()
    parser.read("./query_config.cfg")
    
    # 總共兩個設定檔
    patent_values = get_config_value(parser, 0)
    
    item_list = list(set(open(os.path.join(patent_values[3], patent_values[2])).read().rstrip('\n').split('\n')))

    for item in item_list:
        n = query_one_patent(item, patent_values, results_found)
        results_found = n

    if results_found == 0:
        print("Query returned no results")
    else:
        # Output merged CSV of formatted results.
        json_to_csv.main(patent_values[3], parser.sections()[0], results_found)

        # Clean csv: reorder columns, drop duplicates, sort, then save
        output_filename = os.path.join(patent_values[3], parser.sections()[0]+'.csv')
        df = pd.read_csv(output_filename, dtype=object, encoding='Latin-1')
        df = df[patent_values[5]].drop_duplicates().sort_values(by=patent_values[6][0],
                ascending=[direction != 'desc' for direction in patent_values[6][1]])
        df.to_csv(output_filename, index=False)
        print('({} rows returned)'.format(len(df)))




if __name__ == '__main__':

    query()
