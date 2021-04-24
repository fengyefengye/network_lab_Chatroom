import socket
import threading
import json
from cmd import Cmd


class Client(Cmd):
    prompt = ''
    intro = '[Welcome] Network socket exp: Chatroom\n' + '[Welcome] Enter help for commands\n'

    def __init__(self):
        super().__init__()
        self.my_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.usr_name = None

    def __receive_message_thread(self):
        """
        接受消息线程
        """
        while True:
            # noinspection PyBroadException
            try:
                buffer = self.my_client_socket.recv(1024).decode()
                obj = json.loads(buffer)
                if obj['type'] == 'broadcast':
                    print('[' + str(obj['sender_name']) + '#' + str(obj['sender_id']) + ']', obj['message'])
            except Exception:
                print('[Client] Error: unable to get server data')

    def __send_message_thread(self, message):
        """
        发送消息线程
        :param message: 消息内容
        """
        self.my_client_socket.send(json.dumps({
            'type': 'broadcast',
            'sender_id': self.usr_id,
            'sender_name': self.usr_name,
            'message': message
        }).encode())

    def start(self):
        """
        启动客户端
        """
        self.cmdloop()

    def do_login(self, args):
        """
        登录聊天室
        :param args: 参数
        """
        usrName = args.split(' ')[0]
        self.my_client_socket.connect(('127.0.0.1', 10086))
        # 将昵称发送给服务器，获取用户id
        self.my_client_socket.send(json.dumps({
            'type': 'login',
            'usrName': usrName
        }).encode())
        # 尝试接受数据
        # noinspection PyBroadException
        try:
            buffer = self.my_client_socket.recv(1024).decode()
            obj = json.loads(buffer)
            if obj['type'] == 'login' and obj['res']:
                self.usr_name = usrName
                print('[Client] login to Chatroom successfully')

                # 开启子线程用于接受数据
                thread = threading.Thread(target=self.__receive_message_thread)
                thread.setDaemon(True)
                thread.start()
            else:
                print('[Client] Error: unable to login to Chatroom')
        except Exception:
            print('[Client] Error: unable to get server data')

    def do_send(self, args):
        """
        发送消息
        :param args: 参数
        """
        message = args
        # 显示自己发送的消息
        print('[' + str(self.usr_name) + '(' + str(self.usr_id) + ')' + ']', message)
        # 开启子线程用于发送数据
        thread = threading.Thread(target=self.__send_message_thread, args=(message,))
        thread.setDaemon(True)
        thread.start()

    def do_help(self, arg):
        """
        帮助
        :param arg: 参数
        """
        command = arg.split(' ')[0]
        if command == '':
            print('[Help] login username - login to chatroom using username as you entered')
            print('[Help] send message - send message to everyone as you entered')
        elif command == 'login':
            print('[Help] login username - login to chatroom using username as you entered')
        elif command == 'send':
            print('[Help] send message - send message to everyone as you entered')
        else:
            print('[Help] Invalid command')


if __name__ == '__main__':
    client = Client()
    client.start()
