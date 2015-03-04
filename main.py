# -*- coding: utf-8 -*-

import time
import requests
import psycopg2
from lxml import html, etree
import sys

def insertOrganization(org_name, org_link, org_desc, org_scopes, cur, conn):
    cur.execute("INSERT INTO organizations (org_name, site, description) VALUES ('"
                + org_name.replace("'", "\"").encode("utf-8") + "','"
                + org_link.replace("'", "\"").encode("utf-8") + "','"
                + org_desc.replace("'", "\"").encode("utf-8") + "') RETURNING id;")
    org_id = cur.fetchone()[0]
    for scope_title in org_scopes:
        cur.execute("SELECT id FROM scope_titles WHERE scope_title = '" + scope_title + "';")
        result = cur.fetchone()
        if result is None:
            cur.execute("INSERT INTO scope_titles (scope_title) VALUES ('" + scope_title + "') RETURNING id;")
            result = cur.fetchone()
        scope_title_id = result[0]
        for scope in org_scopes[scope_title]:
            cur.execute("SELECT id FROM scopes WHERE scope_name = '" + scope + "';")
            result = cur.fetchone()
            if result is None:
                cur.execute("INSERT INTO scopes (scope_name) VALUES ('" + scope + "') RETURNING id;")
                result = cur.fetchone()
            scope_id = result[0]
            cur.execute("INSERT INTO scope_linking (scope_title_id, organization_id, scope_id) VALUES (" + str(scope_title_id) + ", " + str(org_id) + ", " + str(scope_id) + ")")
    conn.commit()

log_file = open('log.txt', 'w')
log_file.close()
reload(sys)
sys.setdefaultencoding('utf8')
conn = psycopg2.connect(database="headhunter", host="localhost", port="5432", user="postgres", password="qwerty")
cur = conn.cursor()
millis = int(round(time.time() * 1000))
count = 0
#letters = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'Й', 'К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т', 'У', 'Ф', 'Х', 'Ц', 'Ч', 'Ш', 'Щ', 'Э', 'Ю', 'Я',
#           'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '%23']
#letters = ['%23']
letters = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'Й', 'К', 'Л', 'М', 'Н', 'О', 'П']
for letter in letters:
    page = 0
    while True:
        org_list_response = requests.get('http://krasnoyarsk.hh.ru/employers_list?vacanciesNotRequired=True&letter=' + letter + '&page=' + str(page))
        org_list_doc = html.document_fromstring(org_list_response.text)
        for orgBlock in org_list_doc.cssselect('td.l-cell'):
            for orgLink in orgBlock.cssselect('a'):
                organization_name = orgLink.text
                org_response = requests.get('http://krasnoyarsk.hh.ru' + orgLink.get('href'))
                org_doc = html.document_fromstring(org_response.text)
                organization_link = ''
                for link in org_doc.cssselect('a.company-linkview'):
                    organization_link = link.text
                organization_desc = ''
                desc_block = org_doc.cssselect('div.g-user-content')
                for desc in desc_block:
                    organization_desc = etree.tostring(desc, encoding="UTF-8")\
                        .replace('<div class="g-user-content"><!--noindex-->', '')\
                        .replace('<!--/noindex--></div>', '')
                organization_scopes = {}
                for scope_blocks in org_doc.cssselect('div.profareatree__item'):
                    scope_title = None
                    for scope_block in scope_blocks.getchildren():
                        if scope_block.tag == 'p' and scope_block.cssselect('span')[0] is not None:
                            scope_title = scope_block.cssselect('span')[0].text
                            organization_scopes[scope_title] = []
                        elif scope_block.tag == 'ul':
                            for sub_scope in scope_block.cssselect('li'):
                                sub_scope = sub_scope.cssselect('span')
                                if sub_scope[0] is not None and scope_title is not None:
                                    organization_scopes[scope_title].append(sub_scope[0].text)
                insertOrganization(organization_name,
                                   organization_link,
                                   organization_desc,
                                   organization_scopes,
                                   cur, conn)
                count += 1
                if count % 10 == 0:
                    total_seconds = (int(round(time.time() * 1000)) - millis)//1000
                    seconds = total_seconds%60
                    minutes = (total_seconds//60)%60
                    hours = minutes//60
                    log = 'letter ' + letter + ', page ' + str(page) + ', ' + str(count) + ' orgs, total time ' + str(hours) + ' h ' + str(minutes) + ' m ' + str(seconds) + ' sec'
                    print log
                    if count % 300 == 0:
                        log_file = open('log.txt', 'a')
                        log_file.write(log + "\n")
                        log_file.close()
        if len(org_list_doc.cssselect('div.b-pager__next a.b-pager__next-text')) == 0:
            break
        page += 1
cur.close()
print '###### FINISHED ######'

