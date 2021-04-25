import json
import struct
from socket import *
from common import *
import select
import time
import threading
import datetime
import os

isRunning = True  # 服务端是否正在运行

# 我们需要 一些 缓存
dataBuffer = {}
inputs = {}
outputs = {}
file_dict = {}  # 保存所有服务器接收文件信息的字典 key = 文件名 value = 发送人

# 定义工作线程数量
workerThreadNum = 4


# 给请求文件的client发送文件
def file2client(conn, file_title):
    global file_dict
    with open('server_file/' + str(file_title), 'rb') as f:
        this_file_idx = 0
        while True:
            file_content = f.read(BUFFERSIZE // 2)
            if len(file_content) == 0:
                break
            conn.sendall(packData(bytes('{}'.format({
                'sender_name': file_dict[file_title],
                'file_title': file_title,
                'file_idx': this_file_idx,
                'file_content': file_content
            }), 'utf-8'), UPFILE))
            print('Sending file of {} number = {}'.format(
                file_title,
                this_file_idx
            ))
            this_file_idx = this_file_idx + 1
            time.sleep(FILESLEEP)
        conn.sendall(packData(json.dumps({
            'sender_name': 'System',
            'send_time': datetime.datetime.now().strftime('%H:%M:%S'),
            'message': str(file_title) + ' download successfully.'
        }).encode('utf-8'), NORMAL))


# 广播消息给所有的进程
def broadcast_msg(body, packetType):
    for i in dataBuffer:
        i.sendall(packData(body, packetType))


# 处理接收到的数据包
def dealData(conn, headPack, body, workerId):
    global isRunning, dataBuffer, inputs, outputs, file_dict
    # 数据包类型为HEART_BEAT时
    if headPack[1] == HEART_BEAT:
        conn.send(packData(b'pong!', HEART_BEAT))
    # 数据包类型为NORMAL时
    if headPack[1] == NORMAL:
        my_dict = json.loads(body)
        # 在服务端打印消息
        print('[{}#{}] {}'.format(
            my_dict['sender_name'],
            my_dict['send_time'],
            my_dict['message']
        ))
        # 广播给所有的client
        broadcast_msg(body, NORMAL)

    # 数据包类型为LOGIN时
    if headPack[1] == LOGIN:
        # 服务端打印用户登入的消息
        print('User login> {} has entered the Chatroom'.format(
            json.loads(body)['usr_name']
        ))
        broadcast_msg(body, LOGIN)
    # 数据包类型为SERVERDOWN时
    if headPack[1] == SERVERDOWN:
        sec = json.loads(body)['close_time']
        print('Server will be stopped after {} seconds.'.format(sec))
        body = json.dumps({
            'close_time': sec
        }).encode('utf-8')
        broadcast_msg(body, SERVERDOWN)
        isRunning = False
        time.sleep(sec)
        dataBuffer.clear()
        inputs.clear()
        outputs.clear()

    # 数据包类型为LOGOUT时
    if headPack[1] == LOGOUT:
        while conn in dataBuffer:
            del dataBuffer[conn]
        while conn in inputs[workerId]:
            inputs[workerId].remove(conn)
        while conn in outputs[workerId]:
            outputs[workerId].remove(conn)
        print('User left> {} has left the Chatroom'.format(
            json.loads(body)['usr_name']
        ))
        broadcast_msg(body, LOGOUT)

    # 数据包类型为UPFILE时
    if headPack[1] == UPFILE:
        # my_dict = json.loads(body)
        my_dict = eval(body.decode('utf-8'))
        print('Receive file from {} number = {}'.format(
            my_dict['sender_name'],
            my_dict['file_idx']
        ))
        if my_dict['file_idx'] == 0:
            # file_list.append({
            #     'file_title': my_dict['file_title'],
            #     'sender_name': my_dict['sender_name']
            # })
            file_dict[my_dict['file_title']] = my_dict['sender_name']
            with open('server_file/{}'.format(my_dict['file_title']), 'w') as f:
                f.close()
        with open('server_file/{}'.format(my_dict['file_title']), 'ab') as f:
            f.write(my_dict['file_content'])
            f.close()

    # 数据包类型为GETFILE时
    if headPack[1] == GETFILE:
        conn.sendall(packData(json.dumps({
            'file_dict': file_dict
        }).encode('utf-8'), GETFILE))

    # 数据包类型为DOWNFILE时
    if headPack[1] == DOWNFILE:
        file_title = json.loads(body)['file_name']
        upfile_thread = threading.Thread(target=file2client, args=(conn, file_title))
        upfile_thread.setDaemon(True)
        upfile_thread.start()


# 工作线程, 负责一系列客户端的收发和数据处理
def workerThread(workerId):
    try:
        global isRunning
        # 当前监听的inputs和outputs均为空时, 原地等待
        while (len(inputs[workerId]) + len(outputs[workerId])) <= 0:
            # print(workerId,"<=0")
            time.sleep(0.5)

        while isRunning:
            r_list, w_list, e_list = select.select(inputs[workerId], outputs[workerId], inputs[workerId], 100)
            for obj in r_list:
                data = obj.recv(BUFFERSIZE)
                if data:
                    # 把数据存入缓冲区，类似于push数据
                    dataBuffer[obj] += data

                # 将该连接存到outputs里面等待select
                if obj not in outputs[workerId]:
                    outputs[workerId].append(obj)

            for obj in w_list:
                while len(dataBuffer[obj]) > HEADERSIZE:

                    headPack = struct.unpack('!3I', dataBuffer[obj][:HEADERSIZE])
                    bodySize = headPack[2]

                    if len(dataBuffer[obj]) < HEADERSIZE + bodySize:
                        print("packet (%s Byte) incomplete (total%s Byte), continue receiving..." % (len(dataBuffer[obj]), HEADERSIZE + bodySize))
                        break
                    body = dataBuffer[obj][HEADERSIZE:HEADERSIZE + bodySize]

                    # 数据处理
                    dealData(obj, headPack, body, workerId)

                    # 获取下一个数据包，类似于把数据pop出去
                    if obj not in dataBuffer:
                        break
                    dataBuffer[obj] = dataBuffer[obj][HEADERSIZE + bodySize:]
                    # 处理完后不再监听该socket 直到该socket再次发来数据
                if obj in outputs[workerId]:
                    outputs[workerId].remove(obj)


    except:
        pass


# # 单独开启一个线程开接收server端的输入以控制server是否关闭
# def inputThread():
#     global isRunning
#     while isRunning:
#         input_cmd = input()
#         if input_cmd == '/killall':
#             sec = 3
#             print('Server will be stopped after {} seconds.'.format(sec))
#             body = json.dumps({
#                 'close_time': sec
#             }).encode('utf-8')
#             broadcast_msg(body, SERVERDOWN)
#             isRunning = False
#             time.sleep(sec)
#             dataBuffer.clear()
#             inputs.clear()
#             outputs.clear()
#         else:
#             continue

def myServerSocket():
    global isRunning
    # # 预先启动workerThreadNum个工作线程
    # for i in range(0, workerThreadNum):
    #     inputs[i] = []
    #     outputs[i] = []
    #     worker = threading.Thread(target=workerThread, args=(i,))
    #     worker.start()

    # 接入监听
    server = socket(AF_INET, SOCK_STREAM)
    server.bind(('127.0.0.1', 10086))
    print('Chatroom server start at 127.0.0.1:10086')
    print('Enter /killall to stop it')
    server.listen(5)

    index = 0
    while isRunning:
        conn, client_addr = server.accept()
        conn.setblocking(False)

        inputs[index % workerThreadNum].append(conn)
        dataBuffer[conn] = bytes()

        print('Accept new connection from %s:%s' % client_addr)
        index = index + 1
    server.close()


if __name__ == "__main__":
    # try:
    # # 开启监控server端输入的线程
    # server_input = threading.Thread(target=inputThread)
    # server_input.setDaemon(True)
    # server_input.start()

    basePath = os.path.abspath(os.curdir)
    if not os.path.exists(os.path.join(basePath, 'server_file')):
        os.makedirs(os.path.join(basePath, 'server_file'))

    # try:
    #     os.makedirs('server_file')
    # except:
    #     print('cannot create directory')
    #     pass
    # 预先启动workerThreadNum个工作线程
    for i in range(0, workerThreadNum):
        inputs[i] = []
        outputs[i] = []
        worker = threading.Thread(target=workerThread, args=(i,))
        worker.setDaemon(True)
        worker.start()

    server_socket_thread = threading.Thread(target=myServerSocket)
    server_socket_thread.setDaemon(True)
    server_socket_thread.start()

    while isRunning:
        input_cmd = input()
        if input_cmd == '/killall':
            sec = 3
            print('Server will be stopped after {} seconds.'.format(sec))
            body = json.dumps({
                'close_time': sec
            }).encode('utf-8')
            broadcast_msg(body, SERVERDOWN)
            isRunning = False
            time.sleep(sec)
            dataBuffer.clear()
            inputs.clear()
            outputs.clear()
        else:
            continue

    # # 主线程进行接入监听
    # server = socket(AF_INET, SOCK_STREAM)
    # server.bind(('127.0.0.1', 10086))
    # print('Chatroom server start at 127.0.0.1:10086')
    # print('Enter /killall to stop it')
    # server.listen(5)
    #
    # index = 0
    # while isRunning:
    #     conn, client_addr = server.accept()
    #     conn.setblocking(False)
    #
    #     inputs[index % workerThreadNum].append(conn)
    #     dataBuffer[conn] = bytes()
    #
    #     print('Accept new connection from %s:%s' % client_addr)
    #     index = index + 1
    # except KeyboardInterrupt:
    #     sec = 3
    #     print('Server will be stopped after {} seconds.'.format(sec))
    #     body = json.dumps({
    #         'close_time': sec
    #     }).encode('utf-8')
    #     broadcast_msg(body, SERVERDOWN)
    #     isRunning = False
    #     time.sleep(sec)
    #     dataBuffer.clear()
    #     inputs.clear()
    #     outputs.clear()
    # server.close()
