import struct
from socket import *
from common import packData, HEART_BEAT, NORMAL, HEADERSIZE

# 我们需要一个缓存
dataBuffer = bytes()


# 处理接收到的数据包
def dealData(headPack, body):
    # 数据包类型为HEART_BEAT时
    if headPack[1] == HEART_BEAT:
        conn.send(packData(b'pong!', HEART_BEAT))
    # 其他...


if __name__ == "__main__":

    server = socket(AF_INET, SOCK_STREAM)
    server.bind(('127.0.0.1', 10086))
    server.listen(5)

    conn, client_addr = server.accept()

    while True:
        data = conn.recv(1024)
        if data:
            # 把数据存入缓冲区，类似于push数据
            dataBuffer += data

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

    conn.close()
    server.close()
