#!/usr/bin/env python3
from conjur import Client
import pymysql

client = Client(url="https://xxxx:8443",
                account="myConjurAccount",
                login_id="steven@mysql",
                api_key="10gq5b31sw4x662z72mxd1t4hnth40vdzh2vtb0v2cfhawe3p557wr",
                ssl_verify=False)

ip=client.get('mysql/ip').decode('utf-8')
username=client.get('mysql/username').decode('utf-8')
password=client.get('mysql/password').decode('utf-8')

db = pymysql.connect(host=ip, port=6033, user=username, passwd=password, db='mysql', charset='utf8')

cursor = db.cursor()

sql = 'SELECT VERSION()'

cursor.execute(sql)

data = cursor.fetchone()

print ("Database version : %s " % data)

db.close()
