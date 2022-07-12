## Conjur 實作練習

*12 July 2022. Update: 2022/07/12.*

* [使用環境](#env)
* [目標](#target)
* [操作步驟](#procedure)

<h2 id="env">使用環境</h2>

* Ubuntu 22.04、硬碟 20+ GB、4+ CPU

<h2 id="target">目標</h2>

* 安裝 Conjur/ MySQL  
* 在 Conjur上將 MySQL 的 IP/ USERNAME / PASSWORD 設置上去，並限制由SERVER A取得  
* 在 SERVER A 上以 Python 實作一支 Script，透過 Conjur 的 REST API 取得MySQL 登入資訊後，登入MySQL 執行一個DB QUERY  

<h2 id="procedure">操作步驟</h2>

1. 更新 apt，下載 docker-compose 並新增 docker 群組，以及安裝 git

```
sudo apt-get update ; sudo apt install docker-compose -y ; sudo gpasswd -a $USER docker ; newgrp docker ; sudo apt-get install git-all
```

2. 創建 phpmyadmin 及 mysql 的 docker 路徑

```
mkdir ~/phpmyadmin_mysql && cd phpmyadmin_mysql && mkdir -p conf/mysql && cd ~
```

3. 下載 Conjur 的 docker 包

```
git init ; git clone https://github.com/cyberark/conjur-quickstart.git
```

4. 修改 docker-compose 文件

```
cd conjur-quickstart/ ; vim docker-compose.yml
```

5. 在適當位置貼上以下內容 [docker-compose.yml](https://github.com/StevenHsu22/Conjur)

```yml
  mysql:
    image: mysql:5.7
    container_name: mysql_database
    volumes:
    - ./conf/mysql:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: 自行設定的密碼
      MYSQL_DATABASE: 你想創建的資料庫名稱
      MYSQL_USER: 你想創建的用戶
      MYSQL_PASSWORD: 用戶密碼
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

6. 在 conjur-quickstart 中執行 docker-compose pull 獲取最新的檔案

```
docker-compose pull
```

7. 產生 Conjur 主KEY，並存放到 data_key 檔案內，加入到 Docker 內的 Conjur 預設 KEY；使用 docker-compose up 執行所有在 docker-compose.yml 檔案裡面設定的 Docker Image

```
docker-compose run --no-deps --rm conjur data-key generate > data_key ; export CONJUR_DATA_KEY="$(< data_key)" ; docker-compose up -d
```


8. 確認目前 Docker 容器內執行的程式

```
docker ps -a
```

9. 創建 myConjurAccount 並將 API KEY 存放到 admin_data 檔案中

```
docker-compose exec conjur conjurctl account create myConjurAccount > admin_data
```

10. 初始化帳號

```
docker-compose exec client conjur init -u conjur -a myConjurAccount
```

11. 登入admin帳戶，密碼在 admin_data 檔案中，需複製貼上

```
docker-compose exec client conjur authn login -u admin
```

12. 登入後到存放 policy 的位置新增 mysql.yml 檔案

```
cd conf/policy/ && vi mysql.yml
```

13. mysql.yml 內容 [mysql.yml](https://github.com/StevenHsu22/Conjur)

```yml
- !policy
  id: mysql
  body:
    # Define a human user, a non-human identity that represents an application, and a secret
  - !user steven
  - !host myDemoApp
  - &variables
    - !variable ip
    - !variable username
    - !variable password

  - !permit
    # Give permissions to the human user to update the secret and fetch the secret.
    role: !user steven
    privileges: [read, update, execute]
    resource: *variables

  - !permit
    # Give permissions to the non-human identity to fetch the secret.
    role: !host myDemoApp
    privileges: [read, execute]
    resource: *variables
```

14. 回到 Conjur 主目錄，將剛剛新增的 policy 加入到 Conjur 中

```
cd ~/conjur-quickstart/ && docker-compose exec client conjur policy load root policy/mysql.yml > mysql_data
```

15. 設定變數，並確認是否有設定成功

```
ip=你的IP && username=你設定的 MySQL 用戶 && password=你設定的 MySQL 密碼 && echo $ip,$username,$password
```

16. 將變數新增到 policy 中

```
docker-compose exec client conjur variable values add mysql/ip ${ip} && docker-compose exec client conjur variable values add mysql/username ${username} && docker-     compose exec client conjur variable values add mysql/password ${password}
```

17. 取得認證，並將憑證存放在 conjur_token 檔案內

```
curl -d `mysql_data 檔案中 MyDemoApp 的 API KEY" -k https://你的IP:8443/authn/myConjurAccount/host%2Fmysql%2FmyDemoApp/authenticate > conjur_token
```

18. 抓取憑證，存取為 CONT_SESSION_TOKEN 變數

```
CONT_SESSION_TOKEN=$(cat ~/conjur-quickstart/conjur_token| base64 | tr -d '\r\n')
```                                                  

19. 透過REST API認證取得資訊，並將 IP, USERNAME , PASSWORD 存放到變數中

```
VAR_VALUE_IP=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://你的    IP:8443/secrets/myConjurAccount/variable/mysql%2Fip)
```

```    
VAR_VALUE_USER=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://你的IP:8443/secrets/myConjurAccount/variable/mysql%2Fusername)
```

```
VAR_VALUE_PASSWD=$(curl -s -k -H "Content-Type: application/json" -H "Authorization: Token token=\"$CONT_SESSION_TOKEN\"" https://你的IP:8443/secrets/myConjurAccount/variable/mysql%2Fpassword)
```

20. 確認有無取得 IP、USERNAME、PASSWORD

```
echo "The retrieved value is: $VAR_VALUE_IP"; echo "The retrieved value is: $VAR_VALUE_USER" ; echo "The retrieved value is: $VAR_VALUE_PASSWD"
```

21. 下載 python 的 conjur-client 套件，務必要下載 client 端的，否則會無法使用

```
pip3 install conjur-client
```

22. 撰寫 Python 檔案，在 Conjur 中取得密碼，並連線 MySQL 執行 QUERY 取得 MySQL 版本

```python
#!/usr/bin/env python3
from conjur import Client
import pymysql

client = Client(url='https://你的IP:8443',
                account='myConjurAccount',
                login_id="steven@mysql",
                api_key="你 xxx@mysql 的 API KEY",
                ssl_verify=False)

ip=client.get('mysql/ip').decode('utf-8')
username=client.get('mysql/username').decode('utf-8')
password=client.get('mysql/password').decode('utf-8')

db = pymysql.connect(host=ip, port=6033, user=username, passwd=password, db='test', charset='utf8')

cursor = db.cursor()

sql = 'SELECT VERSION()'

cursor.execute(sql)

data = cursor.fetchone()

print ("Database version : %s " % data)

db.close()
```
