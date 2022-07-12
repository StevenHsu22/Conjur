## Conjur 實作練習

*12 July 2022. Update: 2022/07/12.*

* [使用環境](#env)
* [目標](#target)
* [操作步驟](#procedure)
* [Google評論爬蟲](#googlecrawler)
* [簡易API呈現](#sampleapi)

<h2 id="env">使用環境</h2>

* Ubuntu 22.04、硬碟 20+ GB、4+ CPU

<h2 id="target">目標</h2>

* 安裝 Conjur/ MySQL  
* 在 Conjur上將 MySQL 的 IP/ USERNAME / PASSWORD 設置上去，並限制由SERVER A取得  
* 在 SERVER A 上以 Python 實作一支 Script，透過 Conjur 的 REST API 取得MySQL 登入資訊後，登入MySQL 執行一個DB QUERY  

<h2 id="procedure">操作步驟</h2>

1. 更新 apt，下載 docker-compose 並新增 docker 群組

    sudo apt-get update ; sudo apt install docker-compose -y ; sudo gpasswd -a $USER docker ; newgrp docker


2. 創建phpmyadmin及mysql的docker路徑

    mkdir ~/phpmyadmin_mysql && cd phpmyadmin_mysql && mkdir -p conf/mysql && cd ~

3. 下載Conjur的docker包
```linux
git clone https://github.com/cyberark/conjur-quickstart.git
```
4. 進入Conjur內修改docker包
```linux
cd conjur-quickstart/ vim docker-compose.yml
```

5. 貼上以下內容
```yml
  mysql:
    image: mysql:5.7
    container_name: mysql_database
    volumes:
    - ./conf/mysql:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: `你想設定的root密碼`
      MYSQL_DATABASE: `你想創建的資料庫名稱`
      MYSQL_USER: `你想創建的用戶`
      MYSQL_PASSWORD: `用戶密碼`
    restart: on-failure
    ports:
      - 6033:3306

  phpmyadmin:
    image: phpmyadmin/phpmyadmin
    container_name: pma
    environment:
      PMA_HOST: mysql_database
      PMA_PORT: 3306
      PMA_ARBITRARY: 1
    restart: always
    ports:
      - 8082:80
    depends_on:
      - mysql
```
6. 執行docker-compose
```linux
docker-compose pull
```
7. 產生Conjur主KEY,並存放到data_key檔案內,加入到Docker內的Conjur預設KEY,執行docker-compose
```linux
docker-compose run --no-deps --rm conjur data-key generate > data_key ; export CONJUR_DATA_KEY="$(< data_key)" ; docker-compose up -d
```

8. 確認目前Docker容器內執行的程式
```linux
docker ps -a
```

9. 創建account 並將API KEY存放到 admin_data 檔案中
```linux
docker-compose exec conjur conjurctl account create myConjurAccount > admin_data
```

10. 初始化account
```linux
docker-compose exec client conjur init -u conjur -a myConjurAccount
```
11. 登入admin帳戶，密碼在 admin_data 檔案中，需複製貼上
```linux
docker-compose exec client conjur authn login -u admin
```
12. 登入後到存放policy的位置新增 mysql.yml 檔案
```linux
cd conf/policy/ && vi mysql.yml
```
13. mysql.yml 內容
```yml
- !policy
  id: mysql
  body:
    # Define a human user, a non-human identity that represents an application, and a secret
  - !user Darren
  - !host myDemoApp
  - &variables
    - !variable ip
    - !variable username
    - !variable password

  - !permit
    # Give permissions to the human user to update the secret and fetch the secret.
    role: !user Darren
    privileges: [read, update, execute]
    resource: *variables

  - !permit
    # Give permissions to the non-human identity to fetch the secret.
    role: !host myDemoApp
    privileges: [read, execute]
    resource: *variables
```

14. 回到Conjur主目錄,將剛剛新增的policy加入到Conjur中
```linux
cd ~/conjur-quickstart/ && docker-compose exec client conjur policy load root policy/mysql.yml > mysql_data
```

15. 設定變數，並確認是否有設定成功
```linux
ip=`<你的IP>` && username=`<你設定的MySQL用戶>` && password=`<你設定的MySQL密碼>` && echo $ip,$username,$password
```

16. 將變數新增到policy中
```linux
docker-compose exec client conjur variable values add mysql/ip ${ip} && docker-compose exec client conjur variable values add mysql/username ${username} && docker-compose exec client conjur variable values add mysql/password ${password}
```

17. 取得認證，並將憑證存放在 conjur_token 檔案內
```linux
curl -d `"你的MyDemoApp的API KEY"` -k https://`<你的IP:8443>`/authn/myConjurAccount/host%2Fmysql%2FmyDemoApp/authenticate > conjur_token
```

18. 抓取憑證，存取為 CONT_SESSION_TOKEN 變數
```linux
CONT_SESSION_TOKEN=$(cat ~/conjur-quickstart/conjur_token| base64 | tr -d '\r\n')                                                  
```

19. 透過REST API認證取得資訊，並將 IP, USERNAME , PASSWORD 存放到變數中
```linux
VAR_VALUE_IP=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fip)
```
```linux
VAR_VALUE_USER=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fusername)
```
```linux
VAR_VALUE_PASSWD=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fpassword)
```

20. 確認有無取得 IP, USERNAME , PASSWORD
```linux
echo "The retrieved value is: $VAR_VALUE_IP"
echo "The retrieved value is: $VAR_VALUE_USER"
echo "The retrieved value is: $VAR_VALUE_PASSWD"
```

21. 可以將18~20步驟整合為 bash 檔案如下
```bash
#!/bin/bash
main() {
  CONT_SESSION_TOKEN=$(cat ~/conjur-quickstart/conjur_token| base64 | tr -d '\r\n')
  VAR_VALUE_USER=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fusername)

  VAR_VALUE_PASSWD=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fpassword)

  VAR_VALUE_IP=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://`<你的IP:8443>`/secrets/myConjurAccount/variable/mysql%2Fip)
  echo "The ip is: $VAR_VALUE_IP"
  echo "The username is: $VAR_VALUE_USER"
  echo "The password is: $VAR_VALUE_PASSWD"
}
main "$@"
exit
```
22. 下載python的conjur-client套件，務必要下載client端的，否則會無法使用
```linux
pip3 install conjur-client
```

23. 撰寫Python 檔案，在Conjur中取得密碼，並連線 MySQL 執行QUERY 取得MySQL版本
```python
#!/usr/bin/env python3
from conjur import Client
import pymysql

client = Client(url='https://`<你的IP:8443>`',
                account='myConjurAccount',
                login_id="Darren@mysql",
                api_key="你的API KEY",
                ssl_verify=False)

ip=client.get('mysql/ip').decode('utf-8')
username=client.get('mysql/username').decode('utf-8')
password=client.get('mysql/password').decode('utf-8')

db = pymysql.connect(host='你的IP', port=6033, user=username, passwd=password, db='test', charset='utf8')

cursor = db.cursor()

sql = 'SELECT VERSION()'

cursor.execute(sql)

data = cursor.fetchone()

print ("Database version : %s " % data)

db.close()
```
