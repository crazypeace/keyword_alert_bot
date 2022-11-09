#coding=utf-8
from telethon import TelegramClient, events, sync, errors
from db import utils
import socks,os,datetime
import re as regex
import diskcache
import time
from urllib.parse import urlparse
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.messages import CheckChatInviteRequest
from telethon.tl.functions.channels import DeleteHistoryRequest
from telethon.tl.functions.channels import LeaveChannelRequest, DeleteChannelRequest
from logger import logger
from config import config,_current_path as current_path
from telethon import utils as telethon_utils
from telethon.tl.types import PeerChannel
from telethon.extensions import markdown,html
from asyncstdlib.functools import lru_cache as async_lru_cache
import asyncio

# 配置访问tg服务器的代理
proxy = None
if all(config['proxy'].values()): # 同时不为None
  logger.info(f'proxy info:{config["proxy"]}')
  proxy = (getattr(socks,config['proxy']['type']), config['proxy']['address'], config['proxy']['port'])
# proxy = (socks.SOCKS5, '127.0.0.1', 1088)

account = config['account']
cache = diskcache.Cache(current_path+'/.tmp')# 设置缓存文件目录  当前tmp文件夹。用于缓存分步执行命令的操作，避免bot无法找到当前输入操作的进度
client = TelegramClient('{}/.{}_tg_login'.format(current_path,account['username']), account['api_id'], account['api_hash'], proxy = proxy)
client.start(phone=account['phone'])
# client.start()

# 设置bot，且直接启动
bot = TelegramClient('.{}'.format(account['bot_username']), account['api_id'], account['api_hash'],proxy = proxy).start(bot_token=account['bot_token'])


# client相关操作 目的：读取消息
@client.on(events.MessageEdited)
@client.on(events.NewMessage())
async def on_greeting(event):
    '''Greets someone'''
    if not event.chat:
      logger.error(f'event.chat empty. event: { event }')
      raise events.StopPropagation
    
    if event.chat.username == account['bot_username']: # 不监听当前机器人消息
      logger.debug(f'不监听当前机器人消息, event.chat.username: { event.chat.username }')
      raise events.StopPropagation

    # 是否拒绝来自其它机器人发在群里的消息
    if 'block_bot_msg' in config and config['block_bot_msg']:
      if hasattr(event.message.sender,'bot') and event.message.sender.bot :
        logger.debug(f'不监听所有机器人消息, event.chat.username: { event.chat.username }')
        raise events.StopPropagation
        
    # if not event.is_group:# channel 类型
    if True:# 所有消息类型，支持群组
      message = event.message

      text = message.text
      if message.file and message.file.name:
        text += ' {}'.format(message.file.name)# 追加上文件名

      # 打印消息
      _title = ''
      if not hasattr(event.chat,'title'):
        logger.warning(f'event.chat not found title:{event.chat}')
      else:
        _title = f'event.chat.title:{event.chat.title},'
      logger.debug(f'event.chat.username: {event.chat.username},event.chat.id:{event.chat.id},{_title} event.message.id:{event.message.id},text:{text}')

      # 2.方法：直接发送新消息,非转发.但是可以url预览达到效果

      # 查找当前频道的所有订阅
      sql = """
      select u.chat_id,l.keywords,l.id,l.chat_id
from user_subscribe_list as l  
INNER JOIN user as u on u.id = l.user_id 
where (l.channel_name = ? or l.chat_id = ?)  and l.status = 0  order by l.create_time  desc
      """
      find = utils.db.connect.execute_sql(sql,(event.chat.username,str(event.chat_id))).fetchall()
      if find:
        logger.info(f'channel: {event.chat.username}; all chat_id & keywords:{find}') # 打印当前频道，订阅的用户以及关键字

        for receiver,keywords,l_id,l_chat_id in find:
          try:
            # 消息发送去重规则
            MSG_UNIQUE_RULE_MAP = {
              'SUBSCRIBE_ID': f'{receiver}_{l_id}',
              'MESSAGE_ID': f'{receiver}_{message.id}',
            }
            if 'msg_unique_rule' not in config:
              config['msg_unique_rule'] = 'SUBSCRIBE_ID'
            assert config['msg_unique_rule'] in MSG_UNIQUE_RULE_MAP,'config "msg_unique_rule" error!!!'
            CACHE_KEY_UNIQUE_SEND = MSG_UNIQUE_RULE_MAP[config['msg_unique_rule']]
            logger.debug(f'msg_unique_rule:{config["msg_unique_rule"]} --> {CACHE_KEY_UNIQUE_SEND}')

            # 优先返回可预览url
            channel_url = f'https://t.me/{event.chat.username}/' if event.chat.username else get_channel_url(event.chat.username,event.chat_id)
            channel_msg_url= f'{channel_url}{message.id}'
            send_cache_key = f'_LAST_{l_id}_{message.id}_send'
            if isinstance(event,events.MessageEdited.Event):# 编辑事件
              # 24小时内新建2秒后的编辑不提醒
              if cache.get(send_cache_key) and (event.message.edit_date - event.message.date) > datetime.timedelta(seconds=2): 
                logger.error(f'{channel_msg_url} repeat send. deny!')
                continue
            if not l_chat_id:# 未记录频道id
              logger.info(f'update user_subscribe_list.chat_id:{event.chat_id}  where id = {l_id} ')
              re_update = utils.db.user_subscribe_list.update(chat_id = str(event.chat_id) ).where(utils.User_subscribe_list.id == l_id)
              re_update.execute()
            
            chat_title = event.chat.username if event.chat.username else event.chat.title
            sender = await message.get_sender()

            if is_regex_str(keywords):# 输入为正则字符串
              regex_match = js_to_py_re(keywords)(text)# 进行正则匹配 只支持ig两个flag
              if isinstance(regex_match,regex.Match):#search()结果
                regex_match = [regex_match.group()]
              regex_match_str = []# 显示内容
              for _ in regex_match:
                item = ''.join(_) if isinstance(_,tuple) else _
                if item:
                  regex_match_str.append(item) # 合并处理掉空格
              regex_match_str = list(set(regex_match_str))# 处理重复元素
              if regex_match_str:# 默认 findall()结果
                message_str = f'[#FOUND]({channel_msg_url}) **{regex_match_str}** in {chat_title} @{sender.username}'
                if cache.add(CACHE_KEY_UNIQUE_SEND,1,expire=5):
                  logger.info(f'REGEX: receiver chat_id:{receiver}, l_id:{l_id}, message_str:{message_str}')
                  if isinstance(event,events.NewMessage.Event):# 新建事件
                    cache.set(send_cache_key,1,expire=86400) # 发送标记缓存一天
                  await bot.send_message(receiver, message_str,link_preview = True,parse_mode = 'markdown')
                else:
                  # 已发送该消息
                  logger.debug(f'REGEX send repeat. rule_name:{config["msg_unique_rule"]}  {CACHE_KEY_UNIQUE_SEND}:{channel_msg_url}')
                  continue

              else:
                logger.debug(f'regex_match empty. regex:{keywords} ,message: t.me/{event.chat.username}/{event.message.id}')
            else:#普通模式
              if keywords in text:
                message_str = f'[#FOUND]({channel_msg_url}) **{keywords}** in {chat_title} @{sender.username}'
                if cache.add(CACHE_KEY_UNIQUE_SEND,1,expire=5):
                  logger.info(f'TEXT: receiver chat_id:{receiver}, l_id:{l_id}, message_str:{message_str}')
                  if isinstance(event,events.NewMessage.Event):# 新建事件
                    cache.set(send_cache_key,1,expire=86400) # 发送标记缓存一天
                  await bot.send_message(receiver, message_str,link_preview = True,parse_mode = 'markdown')
                else:
                  # 已发送该消息
                  logger.debug(f'TEXT send repeat. rule_name:{config["msg_unique_rule"]}  {CACHE_KEY_UNIQUE_SEND}:{channel_msg_url}')
                  continue
          except errors.rpcerrorlist.UserIsBlockedError  as _e:
            # User is blocked (caused by SendMessageRequest)  用户已手动停止bot
            logger.error(f'{_e}')
            pass # 关闭全部订阅
          except ValueError  as _e:
            # 用户从未使用bot
            logger.error(f'{_e}')
            # 删除用户订阅和id
            isdel = utils.db.user.delete().where(utils.User.chat_id == receiver).execute()
            user_id = utils.db.user.get_or_none(chat_id=receiver)
            if user_id:
              isdel2 = utils.db.user_subscribe_list.delete().where(utils.User_subscribe_list.user_id == user_id.id).execute()
          except AssertionError as _e:
            raise _e
          except Exception as _e:
            logger.error(f'{_e}')
      else:
        logger.debug(f'sql find empty. event.chat.username:{event.chat.username}, find:{find}, sql:{sql}')

        if 'auto_leave_channel' in config and config['auto_leave_channel']:
          if event.chat.username:# 公开频道/组
            logger.info(f'Leave  Channel/group: {event.chat.username}')
            await leave_channel(event.chat.username)


def js_to_py_re(rx):
  '''
  解析js的正则字符串到python中使用
  只支持ig两个匹配模式
  '''
  query, params = rx[1:].rsplit('/', 1)
  if 'g' in params:
      obj = regex.findall
  else:
      obj = regex.search

  # May need to make flags= smarter, but just an example...    
  return lambda L: obj(query, L, flags=regex.I if 'i' in params else 0)

def is_regex_str(string):
  return regex.search(r'^/.*/[a-zA-Z]*?$',string)

@async_lru_cache(maxsize=256)
async def client_get_entity(entity,_):
  '''
  读取频道信息
  client.get_entity 内存缓存替代方法
  
  尽量避免get_entity出现频繁请求报错 
  A wait of 19964 seconds is required (caused by ResolveUsernameRequest)

  Args:
      entity (_type_): 同get_entity()参数
      _ (_type_): lru缓存标记值
  
  Example:
    缓存 1天
    await client_get_entity(real_id, time.time() // 86400 )

    缓存 10秒
    await client_get_entity(real_id, time.time() // 10 )

  Returns:
      Entity: 
  '''
  return await client.get_entity(entity)



async def cache_set(*args):
  '''
  缓存写入 异步方式

  wiki：https://github.com/grantjenks/python-diskcache/commit/dfad0aa27362354901d90457e465b8b246570c3e

  Returns:
      _type_: _description_
  '''
  loop = asyncio.get_running_loop()
  future = loop.run_in_executor(None, cache.set, *args)
  result = await future
  return result

async def cache_get(*args):
  loop = asyncio.get_running_loop()
  future = loop.run_in_executor(None, cache.get, *args)
  result = await future
  return result
  


# bot相关操作
def parse_url(url):
  """
  解析url信息 
  根据urllib.parse操作 避免它将分号设置为参数的分割符以出现params的问题
  Args:
      url ([type]): [string]
  
  Returns:
      [dict]: [按照个人认为的字段区域名称]  <scheme>://<host>/<uri>?<query>#<fragment>
  """
  if regex.search('^t\.me/',url):
    url = f'http://{url}'

  res = urlparse(url) # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
  result = {}
  result['scheme'],result['host'],result['uri'],result['_params'],result['query'],result['fragment'] = list(res)
  if result['_params'] or ';?' in url:
    result['uri'] += ';'+result['_params']
    del result['_params']
  return result

def get_channel_url(event_chat_username,event_chat__id):
  """
  获取频道/群组 url
  优先返回chat_id的url

  https://docs.telethon.dev/en/latest/concepts/chats-vs-channels.html#converting-ids

  Args:
      event_chat_username (str): 频道名地址 e.g. tianfutong 
      event_chat__id (str): 频道的非官方id。 e.g. -1001630956637
  """
  # event.is_private 无法判断
  # 判断私有频道
  # is_private = True if not event_chat_username else False
  host = 'https://t.me/'
  url = ''
  if event_chat__id:
    real_id, peer_type = telethon_utils.resolve_id(int(event_chat__id)) # 转换为官方真实id
    url = f'{host}c/{real_id}/'
  elif event_chat_username:
    url = f'{host}{event_chat_username}/'
  return url


# 使用说明
@bot.on(events.NewMessage(pattern='/help'))
async def start(event):
  await event.respond('''
目的: 根据关键字过滤频道消息, 群组消息
GitHub: 

主要命令:
 - 订阅关键字
  /add_keyword 关键字1,关键字2
  支持js正则语法: `/[\s\S]*/ig`

 - 取消订阅
  /del_keyword 关键字1,关键字2

 - 取消订阅ID
  /del_id 1,2

 - 取消所有订阅
  /delete_all

 - 显示所有订阅列表
  /list
  ''')
  raise events.StopPropagation


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
  """Send a message when the command /start is issued."""
  # 使用者的telegram ID
  user_id = event.message.chat.id
  # 非公共服务
  if 'private_service' in config and config['private_service'] :
    # 只服务指定的用户
    authorized_users_list = config['authorized_users']
    if user_id not in authorized_users_list :
        await event.respond('Opps! I\'m a private bot. 对不起, 这是一个私人专用的Bot')
        raise events.StopPropagation

  find = utils.db.user.get_or_none(chat_id=user_id)
  if not find:
    insert_res = utils.db.user.create(**{
      'chat_id':user_id,
      'create_time':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
  else: # 存在chat_id
    insert_res = True

  if insert_res:
    await event.respond('Hi! Please input /help , access usage.')
  else:
    await event.respond('Opps! Please try again /start ')
  
  raise events.StopPropagation


@bot.on(events.NewMessage(pattern='/add_keyword'))
async def add_keyword(event):
  """Send a message when the command /add_keyword is issued."""
  # 检查使用者的telegram ID
  await check_user_id(event.message.chat.id)  
  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 用空元素分割
  if len(splitd) <= 1:
    await event.respond('命令格式 /add_keyword 关键字1,关键字2 \n 支持js正则语法: `/[\s\S]*/ig`')
    raise events.StopPropagation
  elif len(splitd)  == 2:
    command, keywords = splitd
    result = await add_keywordlist(keywords.split(','))
    if isinstance(result,str): 
        logger.error('add_keywordlist 错误：'+result)
        await event.respond(result) # 提示错误消息
        raise events.StopPropagation
    else:
      msg = ''
      for key in result:
        msg += f'{key},'
      if msg:
        msg = '订阅成功:\n'+msg 
        text, entities = html.parse(msg)# 解析超大文本 分批次发送 避免输出报错
        for text, entities in telethon_utils.split_text(text, entities):
          await event.respond(text,formatting_entities=entities) 
  raise events.StopPropagation


def check_user_id(user_id)
  find = utils.db.user.get_or_none(chat_id=user_id)
  if not find:# 不存在用户信息
    await event.respond('Failed. Please input /start')
    raise events.StopPropagation


def add_keywordlist(keywords_list):
  """
  订阅关键字
  """
  for keyword in keywords_list:
    keyword = keyword.strip()
    find = utils.db.user_subscribe_list.get_or_none(**{
        'keywords':keyword,
      })
    if find:
      result.append((keyword))
    else:
      insert_res = utils.db.user_subscribe_list.create(**{
        'user_id':'',
        'keywords':keyword,
        'channel_name':'',
        'create_time':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id':''
      })
      if insert_res:
        result.append((keyword))
  return result


@bot.on(events.NewMessage(pattern='/del_keyword'))
async def del_keyword(event):
  """Send a message when the command /del_keyword is issued."""
  # 检查使用者的telegram ID
  await check_user_id(event.message.chat.id)  
  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 删除空元素
  if len(splitd) <= 1:
    await event.respond('命令格式 /del_keyword 关键字1,关键字2')
    raise events.StopPropagation
  elif len(splitd)  == 2:
    command, keywords = splitd
    result = await del_keywordlist(keywords.split(','))
    if isinstance(result,str): 
        logger.error('add_keywordlist 错误：'+result)
        await event.respond(result) # 提示错误消息
        raise events.StopPropagation
    else:
      msg = ''
      for key in result:
        msg += f'{key},'
      if msg:
        msg = '取消订阅成功:\n'+msg 
        text, entities = html.parse(msg)# 解析超大文本 分批次发送 避免输出报错
        for text, entities in telethon_utils.split_text(text, entities):
          await event.respond(text,formatting_entities=entities) 
  raise events.StopPropagation


def del_keywordlist(keywords_list):
  """
  取消订阅关键字
  """
  for keyword in keywords_list:
    keyword = keyword.strip()
    isdel = utils.db.user_subscribe_list.delete().where(utils.User_subscribe_list.keywords == keyword).execute()
    if isdel:
      result.append((keyword))
  return result  


@bot.on(events.NewMessage(pattern='/del_id'))
async def del_id(event):
  '''
  根据id取消关键字订阅
  '''
  # 检查使用者的telegram ID
  await check_user_id(event.message.chat.id)  
  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 删除空元素
  if len(splitd) <= 1:
    await event.respond('命令格式 /del_id 关键字ID1,关键字ID2')
    raise events.StopPropagation
  elif len(splitd)  == 2:
    command, keywords = splitd
    result = await del_keywordidlist(keywords.split(','))
    if isinstance(result,str): 
        logger.error('add_keywordlist 错误：'+result)
        await event.respond(result) # 提示错误消息
        raise events.StopPropagation
    else:
      msg = ''
      for key in result:
        msg += f'{key},'
      if msg:
        msg = '取消订阅成功:\n'+msg 
        text, entities = html.parse(msg)# 解析超大文本 分批次发送 避免输出报错
        for text, entities in telethon_utils.split_text(text, entities):
          await event.respond(text,formatting_entities=entities) 
  raise events.StopPropagation


def del_keywordidlist(keywords_idlist):
  """
  取消订阅关键字
  """
  for keywordid in keywords_idlist:
    keywordid = keywordid.strip()
    find = utils.db.connect.execute_sql('select id,keywords from user_subscribe_list where user_id = %d' % (keywordid,0) ).fetchall()
    if find:
      for id,keywords in find:
        isdel = utils.db.user_subscribe_list.delete().where(utils.User_subscribe_list.id == id).execute()
        if isdel:
          result.append((keywords))          
  return result  


@bot.on(events.NewMessage(pattern='/delete_all'))
async def delete_all(event):
  """Send a message when the command /delete_all is issued."""
  # 检查使用者的telegram ID
  await check_user_id(event.message.chat.id)    
  isdel = utils.db.user_subscribe_list.delete().execute()
  await event.respond('delete_all successfully')
  raise events.StopPropagation
  return result  


# 查询当前所有订阅
@bot.on(events.NewMessage(pattern='/list'))
async def _list(event):
  # 检查使用者的telegram ID
  await check_user_id(event.message.chat.id)  

  find = utils.db.connect.execute_sql('select id,keywords from user_subscribe_list').fetchall()
    if find:
      msg = ''
      for id,keywords in find:
        msg += f'{keywords}\n'
        text, entities = html.parse(msg)# 解析超大文本 分批次发送 避免输出报错
        for text, entities in telethon_utils.split_text(text, entities):
          # await client.send_message(chat, text, formatting_entities=entities)
          await event.respond(text,formatting_entities=entities) 
    else:
      await event.respond('not found list')
  raise events.StopPropagation


if __name__ == "__main__":

    cache.expire()

    # 开启client loop。防止进程退出
    client.run_until_disconnected()
