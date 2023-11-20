# 在原版基础上的修改

https://github.com/Hootrix/keyword_alert_bot/issues/29 信息显示为一行

![image](https://user-images.githubusercontent.com/665889/202410324-6b9b696f-27b0-4730-9491-6508fa30b89a.png)

信息显示末尾添加消息发送人的username 可以直接点击此用户名发起私聊

![image](https://user-images.githubusercontent.com/665889/202411657-e3e75f5d-3447-41cf-b021-a3a385c94d3b.png)


config.yaml 不考虑旧版本的配置文件兼容性问题

![image](https://user-images.githubusercontent.com/665889/202410665-68ebbc74-ed29-47cc-9060-b03f86390c25.png)

![image](https://user-images.githubusercontent.com/665889/202412458-717e0601-ff61-42c0-9adb-e0912ec7e5e1.png)


# 写给新手的搭建指南
## 1. 账户
### Create Telelgram Account & API
https://my.telegram.org/apps

开通api 建议请使用新注册的Telegram账户

得到 api_id, api_hash
![chrome_2022-08-08_11-04-17](https://user-images.githubusercontent.com/665889/183333531-ea69d6c8-b720-4efa-9c6e-fc31f2b5a252.png)

### Create BOT
https://t.me/BotFather

/start

/newbot

bot的name

bot的username

得到 token to access the HTTP API

![Telegram_2022-08-08_10-57-30](https://user-images.githubusercontent.com/665889/183334493-b6a906b4-bf0a-45ae-91be-ed1e5f2f2aa4.png)

## 2. 运行环境

### 准备python相关组件
基于Debian 11 环境
```
apt update
apt install -y pip 
pip install telethon peewee PySocks diskcache PyYAML asyncstdlib colorama text_box_wrapper
```

### 从GitHub拉程序文件
获得压缩包地址

![image](https://user-images.githubusercontent.com/665889/183339082-e409da96-6dfe-46e4-a592-9c434ebfd0bd.png)

```
cd 
wget -N https://github.com/crazypeace/keyword_alert_bot/archive/refs/heads/master.zip
unzip master.zip
cd keyword_alert_bot-master/
```

## 3. 配置文件config.yml

修改如下字段

![Notepad3_2022-08-08_11-09-15-1](https://user-images.githubusercontent.com/665889/183334604-854fecfe-9499-4dd0-bfb2-b85a29a4baa8.png)

phone 改为你的新Telegram账户的电话号码

username 改为你的新Telegram账户的username

## 4. 第一次运行bot
```
python3 ./main.py
```

脚本窗口提示你输入验证码，同时，你的新Telegram账户会收到一个验证码

![image](https://user-images.githubusercontent.com/665889/183342317-6fd4e4a3-5670-4f97-b09c-11f8236024d8.png)

将这个验证码输入到脚本窗口

## 5. 长期运行bot

### 用screen在后台运行

```
apt install -y screen
screen
python3 ./main.py
```

### 用crontab计划任务

```
crontab -e
```
第一次运行会提示你用哪个编辑器，选你喜欢的就好，小白推荐用nano，操作起来和Win的notepad比较像

输入下面这行再保存

```
@reboot ( sleep 120 ; python3 /etc/keyword_alert_bot-master/main.py )
```

意思是每次重启后，等待120秒，再执行后面那句shell命令

# 🤖Telegram keyword alert bot ⏰


用于提醒 频道/群组 关键字消息

如果想订阅`群组`消息，确保普通TG账户加入该群组不需要验证。

原理：tg命令行客户端来监听消息，使用bot来发送消息给订阅用户。

👉  Features：

- [x] 关键字消息订阅：根据设定的关键字和频道来发送新消息提醒
- [x] 支持正则表达式匹配语法
- [x] 支持多频道订阅 & 多关键字订阅
- [x] 支持订阅群组消息
- [x] 支持私有频道ID/邀请链接的消息订阅 

  1. https://t.me/+B8yv7lgd9FI0Y2M1  
  2. https://t.me/joinchat/B8yv7lgd9FI0Y2M1 
  

👉 Todo:

- [ ] 私有群组订阅和提醒
- [ ] 私有频道消息提醒完整内容预览
- [ ] 多账号支持
- [ ] 扫描退出无用频道/群组

# DEMO

http://t.me/keyword_alert_bot

![image](https://user-images.githubusercontent.com/10736915/171514829-4186d486-e1f4-4303-b3a9-1cfc1b571668.png)


# USAGE

## 普通关键字匹配

```
/subscribe   免费     https://t.me/tianfutong
/subscribe   优惠券   https://t.me/tianfutong

```

## 正则表达式匹配

使用js正则语法规则，用/包裹正则语句，目前可以使用的匹配模式：i,g

```
# 订阅手机型号关键字：iphone x，排除XR，XS等型号，且忽略大小写
/subscribe   /(iphone\s*x)(?:[^sr]|$)/ig  com9ji,xiaobaiup
/subscribe   /(iphone\s*x)(?:[^sr]|$)/ig  https://t.me/com9ji,https://t.me/xiaobaiup

# xx券
/subscribe  /([\S]{2}券)/g  https://t.me/tianfutong

```

## BOT HELP

```

目的：根据关键字订阅频道消息

支持多关键字和多频道订阅，使用英文逗号`,`间隔

关键字和频道之间使用空格间隔

主要命令：

/subscribe - 订阅操作： `关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe - 取消订阅： `关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe_all - 取消所有订阅

/list - 显示所有订阅列表

---

Purpose: Subscribe to channel messages based on keywords

Multi-keyword and multi-channel subscription support, using comma `,` interval.

Use space between keywords and channels

Main command:

/subscribe - Subscription operation: `keyword1,keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe - unsubscribe: `keyword1,keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe_all - cancel all subscriptions

/list - displays a list of all subscriptions
```
