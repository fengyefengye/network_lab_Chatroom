import json
import struct
from socket import *
from common import *
import threading
import time
import datetime
import os

# 我们需要一个缓存
dataBuffer = bytes()
# 未收到回应的心跳包计数
heartBeatCount = 0
# 是否在聊天室中
AFK_n = True
# 是否是聊天室的管理员
sudo_flag = False
# 用户名
usr_name = ''


# 心跳包线程:
def sendHeartBeat():
    global heartBeatCount, AFK_n
    while AFK_n:
        # print("客户端发送心跳包, Ping!")
        client.send(packData(b'ping!', HEART_BEAT))
        heartBeatCount = heartBeatCount + 1
        if heartBeatCount > 3:
            # 后续处理
            AFK_n = False
            print("ERROR: Failed connecting to Chatroom, please check your connection and try again!")
            client.close()

        time.sleep(3)


def upload_file(file_url):
    global usr_name
    try:
        if os.path.isfile(file_url):
            with open(file_url, 'rb') as f:
                file_idx = 0
                file_title = os.path.basename(file_url)
                while True:
                    file_content = f.read(BUFFERSIZE / 2)
                    if len(file_content) == 0:
                        break
                    client.sendall(packData(json.dumps({
                        'sender_name': usr_name,
                        'file_title': file_title,
                        'file_idx': file_idx,
                        'file_content': file_content
                    }).encode('utf-8'), UPFILE))
                    file_idx = file_idx + 1
                    time.sleep(0.01)
                client.sendall(packData(json.dumps({
                    'sender_name': usr_name,
                    'send_time': datetime.datetime.now().strftime('%H:%M:%S'),
                    'message': 'Upload file ' + str(file_title) + ' to server'
                }), NORMAL))
        else:
            print('Error: not a file')
    except:
        print('Error: cannot open file, invalid URL')


# 发消息线程:
def sendMsg():
    global usr_name, sudo_flag, AFK_n
    while AFK_n:
        user_input = input()
        msg = json.dumps({
            'sender_name': usr_name,
            'send_time': datetime.datetime.now().strftime('%H:%M:%S'),
            'message': user_input
        }).encode('utf-8')
        # if command == 'login':  # 登入命令
        #     usr_name = msg
        #     client.sendall(packData(json.dumps({
        #         'usr_name': usr_name
        #     }).encode('utf-8'), LOGIN))
        # if command == 'send':  # 发送消息命令
        #     client.sendall(packData(json.dumps({
        #         'sender_name': usr_name,
        #         'send_time': datetime.datetime.now().strftime('%H:%M:%S'),
        #         'message': msg
        #     }).encode('utf-8'), NORMAL))
        if user_input == '':
            continue
        elif user_input == '/quit':  # 退出命令
            AFK_n = False
            client.sendall(packData(json.dumps({
                'usr_name': usr_name
            }).encode('utf-8'), LOGOUT))
            time.sleep(0.5)
            try:
                client.close()
            except ConnectionAbortedError:
                pass
            finally:
                print('You have left the chatroom.')
                # exit(0)
        elif user_input == '/sudo':  # 进入sudo模式
            if not sudo_flag:
                passwd = input('Enter password: ')
                if passwd == 'admin':
                    sudo_flag = True
                    print('Successfully entered sudo mode.')
                else:
                    print('invalid password')
            else:
                print('Already under sudo mode.')
        elif user_input == '/exit':  # 退出sudo模式
            if sudo_flag:
                sudo_flag = False
            else:
                print('You are not admin.')
        elif user_input == '/killall':  # 关闭服务器
            if sudo_flag:
                client.sendall(packData(json.dumps({
                    'close_time': 3
                }).encode('utf-8'), SERVERDOWN))
                break
            else:
                print('You must be admin to use this command.')
        elif user_input == '/upfile': # 上传文件
            file_url = input('Enter the url of file: ')
            upfile_thread = threading.Thread(target=upload_file, args=(file_url,))
            upfile_thread.setDaemon(True)
            upfile_thread.start()
        elif user_input == '/help':  # 帮助命令
            print('''
            /quit   : leave chatroom
            /sudo   : enter sudo mode
            /upfile : upload file to server
            /exit   : exit sudo mode [sudo]
            /killall: shutdown the chatroom server [sudo]
            /help   : get help message
            ''')

        else:
            client.sendall(packData(msg, NORMAL))


# 处理接收到的数据包
def dealData(headPack, body):
    global heartBeatCount, AFK_n, usr_name
    # 数据包类型为HEART_BEAT时
    if headPack[1] == HEART_BEAT:
        # print("客户端收到服务端返回心跳包, Pong!")
        heartBeatCount = heartBeatCount - 1
    # 数据包类型为NORMAL时
    if headPack[1] == NORMAL:
        my_dict = json.loads(body)
        # 按照格式打印消息
        print('[{}#{}] {}'.format(
            my_dict['sender_name'],
            my_dict['send_time'],
            my_dict['message']
        ))
    # 数据包类型为LOGIN时
    if headPack[1] == LOGIN:
        # 打印用户登入信息
        print('User login> {} has entered the Chatroom'.format(
            json.loads(body)['usr_name']
        ))
    # 数据包类型为LOGOUT时
    if headPack[1] == LOGOUT:
        my_dict = json.loads(body)
        print('User left> {} has left the the Chatroom'.format(
            my_dict['usr_name']
        ))
    # 数据包类型为SERVERDOWN时
    if headPack[1] == SERVERDOWN:
        print('> Chatroom server will be closed after {} seconds.'.format(
            json.loads(body)['close_time']
        ))
        AFK_n = False
        client.close()
        # exit(0)


if __name__ == "__main__":
    usr_name = input('[Welcome] Network socket exp: Chatroom, Please enter your username: ')

    client = socket(AF_INET, SOCK_STREAM)
    # if client.connect(('127.0.0.1', 10086)):
    #     print("[Welcome] Successfully connected to Chatroom.")
    #     print('[Welcome] Enter /help for commands.')
    #     client.sendall(packData(json.dumps({
    #         'usr_name': usr_name
    #     }).encode('utf-8'), LOGIN))

    client.connect(('127.0.0.1', 10086))
    print("[Welcome] Successfully connected to Chatroom.")
    print('[Welcome] Enter /help for commands.')
    client.sendall(packData(json.dumps({
        'usr_name': usr_name
    }).encode('utf-8'), LOGIN))

    heartBeatThread = threading.Thread(target=sendHeartBeat, name='heartBeatThread')
    sendMsgThread = threading.Thread(target=sendMsg, name='sendMsgThread')
    heartBeatThread.setDaemon(True)
    sendMsgThread.setDaemon(True)
    sendMsgThread.start()
    heartBeatThread.start()

    while AFK_n:
        try:
            data = client.recv(BUFFERSIZE)
            if data:
                # 把数据存入缓冲区，类似于push数据
                dataBuffer += data
        except:
            pass

        while len(dataBuffer) > HEADERSIZE:

            headPack = struct.unpack('!3I', dataBuffer[:HEADERSIZE])
            bodySize = headPack[2]

            if len(dataBuffer) < HEADERSIZE + bodySize:
                print("数据包（%s Byte）不完整（总共%s Byte），继续接受 " % (len(dataBuffer), HEADERSIZE + bodySize))
                break

            body = dataBuffer[HEADERSIZE:HEADERSIZE + bodySize]

            # 数据处理
            dealData(headPack, body)

            # 获取下一个数据包，类似于把数据pop出去
            dataBuffer = dataBuffer[HEADERSIZE + bodySize:]

    client.close()
