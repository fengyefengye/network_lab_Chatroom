import socket
import threading
import json


class Server:
    """
    服务器类
    """

    def __init__(self):
        """
        构造
        """
        self.my_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn_list = list()

    def __user_thread(self):
        """
        用户子线程
        :param user_id: 用户id
        """
        connection = self.conn_list[user_id]
        usrName = self.usr_name_list[user_id]
        print(str(usrName) + 'has entered Chatroom')
        self.msg_broadcast(message=str(usrName) + 'has entered Chatroom')

        # 侦听
        while True:
            # noinspection PyBroadException
            try:
                buffer = connection.recv(1024).decode()
                # 解析成json数据
                obj = json.loads(buffer)
                # 如果是广播指令
                if obj['type'] == 'broadcast':
                    self.msg_broadcast(obj['sender_id'], obj['sender_name'], obj['message'])
                    print('[' + str(obj['sender_name']) + '#' + str(obj['sender_id']) + ']', obj['message'])
                else:
                    print('[Server] Error: decode json patch error:', connection.getsockname(), connection.fileno())
            except Exception:
                print('[Server] Error: connection failed:', connection.getsockname(), connection.fileno())
                self.conn_list[user_id].close()
                self.conn_list[user_id] = None
                self.usr_name_list[user_id] = None

    def msg_broadcast(self, user_id=0, username='System', message=''):
        """
        广播
        :param user_id: 用户id(0为系统)
        :param message: 广播内容
        """
        for i in range(1, len(self.conn_list)):
            if user_id != i:
                self.conn_list[i].send(json.dumps({\
                    'type': 'broadcast',
                    'sender_id': user_id,
                    'sender_name': username,
                    'message': message
                }).encode())

    def run_server(self):
        """
        启动服务器
        """
        # 绑定端口
        self.my_server_socket.bind(('127.0.0.1', 10086))
        # 启用监听
        self.my_server_socket.listen(5000)
        print('[Server] server running at 127.0.0.1:10086 ...')

        # 清空连接
        self.conn_list.clear()
        self.usr_name_list.clear()
        self.conn_list.append(None)
        self.usr_name_list.append('System')

        # 开始侦听
        while True:
            connection, address = self.my_server_socket.accept()
            print('[Server] receive new connection from client', connection.getsockname(), connection.fileno())

            # 尝试接受数据
            # noinspection PyBroadException
            try:
                buffer = connection.recv(1024).decode()
                # 解析成json数据
                obj = json.loads(buffer)
                # 如果是连接指令，那么则返回一个新的用户编号，接收用户连接
                if obj['type'] == 'login':
                    self.conn_list.append(connection)
                    connection.send(json.dumps({
                        'type': 'login',
                        'res': 1
                    }).encode())

                    # 开辟一个新的线程
                    thread = threading.Thread(target=self.__user_thread)
                    thread.setDaemon(True)
                    thread.start()
                else:
                    print('[Server] Error: decode json patch error:', connection.getsockname(), connection.fileno())
            except Exception:
                print('[Server] Error: unable to receive data:', connection.getsockname(), connection.fileno())


if __name__ == '__main__':
    server = Server()
    server.run_server()
