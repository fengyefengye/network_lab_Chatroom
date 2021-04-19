import socket
import threading
import json

serverIP = '127.0.0.1'
serverPort = 10086

class Server:
    """
    服务器类
    """
    def __init__(self):
        """
        构造
        """
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connections = list()
        self.__nicknames = list()
        # self.serverDict = dict() # server 端存储 client usrName 和 usrId 的字典

    def __user_thread(self, user_id):
        """
        用户子线程
        :param user_id: 用户id
        """
        connection = self.__connections[user_id]
        nickname = self.__nicknames[user_id]
        print('[Server] 用户', user_id, nickname, '加入聊天室')
        self.__broadcast(message='用户 ' + str(nickname) + '(' + str(user_id) + ')' + '加入聊天室')

        # 侦听
        while True:
            # noinspection PyBroadException
            try:
                buffer = connection.recv(1024).decode()
                # 解析成json数据
                obj = json.loads(buffer)
                # 如果是广播指令
                if obj['cmd_type'] == 'broadcast':
                    self.__broadcast(obj['sender_usrId'], obj['message'])
                    print('[', self.__nicknames[obj['sender_usrId']],']', obj['message'])
                else:
                    print('[Server] 无法解析json数据包:', connection.getsockname(), connection.fileno())
            except Exception:
                print('[Server] 连接失效:', connection.getsockname(), connection.fileno())
                self.__connections[user_id].close()
                self.__connections[user_id] = None
                self.__nicknames[user_id] = None

    def __broadcast(self, user_id=0, message=''):
        """
        广播
        :param user_id: 用户id(0为系统)
        :param message: 广播内容
        """
        for i in range(1, len(self.__connections)):
            if user_id != i:
                self.__connections[i].send(json.dumps({
                    'sender_usrId': user_id,
                    'sender_usrName': self.__nicknames[user_id],
                    'message': message
                }).encode())

    def start(self):
        """
        启动服务器
        """
        # 绑定端口
        self.serverSocket.bind((serverIP, serverPort))
        # 启用监听
        self.serverSocket.listen(10)
        print('[Server] 服务器正在运行......')

        # 清空连接
        self.__connections.clear()
        self.__nicknames.clear()
        # self.serverDict.clear()
        # self.serverDict.setdefault(0, 'Server')
        self.__connections.append(None)
        self.__nicknames.append('System')

        # 开始侦听
        while True:
            connection, address = self.serverSocket.accept()
            print('[Server] 收到新的client连接请求', connection.getsockname(), connection.fileno())
            
            
            # 尝试接受数据
            # noinspection PyBroadException
            try:
                buffer = connection.recv(1024).decode()
                # 解析成json数据
                obj = json.loads(buffer)
                # 如果是连接指令，那么则返回一个新的用户编号，接收用户连接
                if obj['cmd_type'] == 'login':
                    self.__connections.append(connection)
                    self.__nicknames.append(obj['nickname'])
                    connection.send(json.dumps({
                        'id': len(self.__connections) - 1
                    }).encode())
                    

                    # 开辟一个新的线程
                    thread = threading.Thread(target=self.__user_thread, args=(len(self.__connections) - 1, ))
                    thread.setDaemon(True)
                    thread.start()
                else:
                    print('[Server] 无法解析json数据包:', connection.getsockname(), connection.fileno())
            except Exception:
                print('[Server] 无法接受数据:', connection.getsockname(), connection.fileno())
