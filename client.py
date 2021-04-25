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
# client状态: 是否运行
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
                    file_content = f.read(BUFFERSIZE // 2)
                    if len(file_content) == 0:
                        break
                    # client.sendall(packData(json.dumps({
                    #     'sender_name': usr_name,
                    #     'file_title': file_title,
                    #     'file_idx': file_idx,
                    #     'file_content': file_content
                    # }).encode('utf-8'), UPFILE))
                    # json无法打包bytes类型，只能用bytes发送
                    client.sendall(packData(bytes('{}'.format({
                        'sender_name': usr_name,
                        'file_title': file_title,
                        'file_idx': file_idx,
                        'file_content': file_content
                    }), 'utf-8'), UPFILE))
                    file_idx = file_idx + 1
                    time.sleep(FILESLEEP)
                client.sendall(packData(json.dumps({
                    'sender_name': usr_name,
                    'send_time': datetime.datetime.now().strftime('%H:%M:%S'),
                    'message': 'Upload file ' + str(file_title) + ' to server'
                }).encode('utf-8'), NORMAL))
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
        elif user_input == '/upfile':  # 上传文件
            file_url = input('Enter the absolute path of file: ')
            upfile_thread = threading.Thread(target=upload_file, args=(file_url,))
            upfile_thread.setDaemon(True)
            upfile_thread.start()
        elif user_input == '/getfile':  # 查看服务中的所有文件
            client.sendall(packData(json.dumps({
                'file_dict': {}
            }).encode('utf-8'), GETFILE))
        elif user_input == '/downfile':  # 从服务器下载文件
            file_name = input('Please enter the file name you want to download: ')
            client.sendall(packData(json.dumps({
                'file_name': file_name
            }).encode('utf-8'), DOWNFILE))
        elif user_input == '/help':  # 帮助命令
            print('''
            /quit    : leave chatroom
            /sudo    : enter sudo mode
            /upfile  : upload file to server
            /getfile : get all file information in server
            /downfile: download specific file from server
            /exit    : exit sudo mode [sudo]
            /killall : shutdown the chatroom server [sudo]
            /help    : get help message
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

    # 数据包类型为UPFILE时
    if headPack[1] == UPFILE:
        my_dict = eval(body.decode('utf-8'))
        if my_dict['file_idx'] == 0:
            with open('client_files/{}/{}'.format(
                usr_name,
                my_dict['file_title']
            ), 'w') as f:
                f.close()
        with open('client_files/{}/{}'.format(
            usr_name,
            my_dict['file_title']
        ), 'ab') as f:
            f.write(my_dict['file_content'])
            f.close()

    # 数据包类型为GETFILE时
    if headPack[1] == GETFILE:
        file_dict = json.loads(body)['file_dict']
        print('> Getting all files in server...<file name> <- <sender>')
        for key, value in file_dict.items():
            print('{} <- {}'.format(
                key,
                value
            ))


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

    # try:
    #     os.makedirs('client_files')
    # except:
    #     pass
    basePath = os.path.abspath(os.curdir)
    if not os.path.exists(os.path.join(basePath, 'client_files')):
        os.makedirs(os.path.join(basePath, 'client_files'))
    if not os.path.exists(os.path.join(basePath, 'client_files/{}'.format(usr_name))):
        os.makedirs(os.path.join(basePath, 'client_files/{}'.format(usr_name)))

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
                print("packet (%s Byte) incomplete (total%s Byte), continue receiving..." % (len(dataBuffer), HEADERSIZE + bodySize))
                break

            body = dataBuffer[HEADERSIZE:HEADERSIZE + bodySize]

            # 数据处理
            dealData(headPack, body)

            # 获取下一个数据包，类似于把数据pop出去
            dataBuffer = dataBuffer[HEADERSIZE + bodySize:]

    client.close()
