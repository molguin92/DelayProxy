#  Copyright 2019 Manuel Olguín Muñoz <manuel@olguin.se><molguin@kth.se>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import socket
import time
import numpy as np
from multiprocessing import Event, Pool
from multiprocessing.pool import AsyncResult
from typing import Callable, Union
from aiologger import Logger


class BaseDelayProxy:
    SHUTDOWN_TIMEOUT = 3

    def __init__(self,
                 listen_host: str = '0.0.0.0',
                 listen_port: int = 5000,
                 connect_host: str = '0.0.0.0',
                 connect_port: int = 5001,
                 chunk_size: int = 4096,
                 delay_dist: Callable[[], float] = lambda: 0):
        super().__init__()
        self.listen_addr = (listen_host, listen_port)
        self.connect_addr = (connect_host, connect_port)
        self.log = Logger.with_default_handlers(name=self.__name__)
        self.shutdown_signal = Event()
        self.delay_dist = delay_dist
        self.chunk_size = chunk_size

        self.result: AsyncResult = None
        self.ppool: Pool = None
        self.conn_A: socket.SocketType = None
        self.conn_B: socket.SocketType = None

    @staticmethod
    def __relay(conn_A: socket.SocketType,
                conn_B: socket.SocketType,
                chunk_size: int = 4096,
                delay_dist: Callable[[], float] = lambda: 0,
                shutdown_event: Event = Event()) -> None:
        shutdown_event.clear()
        while not shutdown_event.is_set():
            # read from A, wait X time, send to B
            data = conn_A.recv(chunk_size)
            time.sleep(delay_dist())
            conn_B.sendall(data)

    def __setup(self) -> Union[socket.SocketType, socket.SocketType]:
        l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        l_sock.bind(self.listen_addr)
        l_sock.listen(0)
        self.conn_A, addr_A = l_sock.accept()
        self.log.info(f'Accepted connection from {addr_A}')

        self.conn_B = socket.create_connection(self.connect_addr)
        self.log.info(f'Connected to {self.connect_addr}')

    def start(self) -> None:
        self.__setup()
        self.ppool = Pool(2)
        self.result = self.ppool.apply_async(
            BaseDelayProxy.__relay,
            (self.conn_A, self.conn_B),
            {'chunk_size'    : self.chunk_size,
             'shutdown_event': self.shutdown_signal,
             'delay_dist'    : self.delay_dist})
        self.ppool.close()

    def stop(self):
        self.shutdown_signal.set()
        if self.conn_A:
            self.conn_A.shutdown(socket.SHUT_RDWR)
            self.conn_A.close()

        if self.conn_B:
            self.conn_B.shutdown(socket.SHUT_RDWR)
            self.conn_B.close()

        if self.result and self.ppool:
            try:
                self.result.get(self.SHUTDOWN_TIMEOUT)
            except TimeoutError:
                self.ppool.terminate()

            self.ppool.join()


class NormalDelayProxy(BaseDelayProxy):
    def __init__(self,
                 mean,
                 std_dev,
                 listen_host: str = '0.0.0.0',
                 listen_port: int = 5000,
                 connect_host: str = '0.0.0.0',
                 connect_port: int = 5001,
                 chunk_size: int = 4096):
        super().__init__(
            listen_host=listen_host,
            listen_port=listen_port,
            connect_host=connect_host,
            connect_port=connect_port,
            chunk_size=chunk_size,
            delay_dist=lambda: np.random.normal(mean, std_dev))


class ExponentialDelayProxy(BaseDelayProxy):
    def __init__(self,
                 scale,
                 listen_host: str = '0.0.0.0',
                 listen_port: int = 5000,
                 connect_host: str = '0.0.0.0',
                 connect_port: int = 5001,
                 chunk_size: int = 4096):
        super().__init__(
            listen_host=listen_host,
            listen_port=listen_port,
            connect_host=connect_host,
            connect_port=connect_port,
            chunk_size=chunk_size,
            delay_dist=lambda: np.random.exponential(scale=scale))
