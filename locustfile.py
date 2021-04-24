# coding: utf-8
import time
from socket import *
from locust import TaskSet, task, between, Locust, events, User
import struct

from common import packData, HEART_BEAT, NORMAL, HEADERSIZE


class SocketUser(User):
    # 目标地址
    host = "127.0.0.1"
    # 目标端口
    port = 10086
    # 等待时间, 用户连续的请求之间随机等待0.1~1s
    wait_time = between(0.1, 1)

    def __init__(self, *args, **kwargs):
        super(SocketUser, self).__init__(*args, **kwargs)
        self.client = socket(AF_INET, SOCK_STREAM)

    def on_start(self):
        self.client.connect((self.host, self.port))

    def on_stop(self):
        self.client.close()

    @task(100)
    def sendHeartBeat(self):
        start_time = time.time()
        try:
            self.client.send(packData(b'Hello Server Are you OK?', NORMAL))
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(request_type="Normal", name="SendMessage", response_time=total_time,
                                        response_length=0, exception=e)
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(request_type="Normal", name="SendMessage", response_time=total_time,
                                        response_length=0)

        start_time = time.time()
        try:
            data = self.client.recv(1024)
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(request_type="Normal", name="RecvMessage", response_time=total_time,
                                        response_length=0, exception=e)
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(request_type="Normal", name="RecvMessage", response_time=total_time,
                                        response_length=0)
