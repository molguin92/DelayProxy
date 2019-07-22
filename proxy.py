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
from multiprocessing import Barrier, Event, Pool
from multiprocessing.pool import AsyncResult
from typing import Callable, Optional, Union

from distributions import Distribution, ConstantDistribution


def pool_init(shutdown_signal: Event):
    global shutdown_event
    shutdown_event = shutdown_signal


def relay(conn_A: socket.SocketType,
          conn_B: socket.SocketType,
          barrier: Barrier = None,
          chunk_size: int = 4096,
          delay_dist: Distribution = ConstantDistribution(constant=0.0)) \
        -> None:
    try:
        while not shutdown_event.is_set():
            # read from A, wait X time, send to B
            data = conn_A.recv(chunk_size)
            time.sleep(delay_dist.sample())
            conn_B.sendall(data)
    except socket.error:
        # todo: log error
        pass
    except Exception as e:
        print(e)

    if barrier:
        barrier.wait()


class DelayProxy:
    SHUTDOWN_TIMEOUT = 3

    __relay = staticmethod(relay)

    def __init__(self,
                 listen_host: str = '0.0.0.0',
                 listen_port: int = 5000,
                 connect_host: str = '0.0.0.0',
                 connect_port: int = 5001,
                 chunk_size: int = 4096,
                 barrier: Barrier = None,
                 delay_dist: Distribution = ConstantDistribution(constant=0.0)):
        super().__init__()
        self.listen_addr = (listen_host, listen_port)
        self.connect_addr = (connect_host, connect_port)
        self.shutdown_signal = Event()
        self.delay_dist = delay_dist
        self.chunk_size = chunk_size

        self.result_AtoB: Optional[AsyncResult] = None
        self.result_BtoA: Optional[AsyncResult] = None
        self.ppool: Optional[Pool] = None
        self.conn_A: Optional[socket.SocketType] = None
        self.conn_B: Optional[socket.SocketType] = None
        self.barrier = barrier

    def __setup(self) -> Union[socket.SocketType, socket.SocketType]:
        l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        l_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        l_sock.bind(self.listen_addr)
        l_sock.listen(0)
        self.conn_A, addr_A = l_sock.accept()
        # self.log.info(f'Accepted connection from {addr_A}')

        self.conn_B = socket.create_connection(self.connect_addr)
        # self.log.info(f'Connected to {self.connect_addr}')

    def start(self) -> None:
        self.__setup()
        self.ppool = Pool(2,
                          initializer=pool_init,
                          initargs=(self.shutdown_signal,))
        self.result_AtoB = self.ppool.apply_async(
            DelayProxy.__relay,
            (self.conn_A, self.conn_B),
            {'chunk_size': self.chunk_size,
             'delay_dist': self.delay_dist})
        self.result_BtoA = self.ppool.apply_async(
            DelayProxy.__relay,
            (self.conn_B, self.conn_A),
            {'chunk_size': self.chunk_size,
             'delay_dist': self.delay_dist})
        self.ppool.close()

    def stop(self):
        self.shutdown_signal.set()
        try:
            if self.conn_A:
                self.conn_A.shutdown(socket.SHUT_RDWR)
                self.conn_A.close()
        except OSError:
            pass

        try:
            if self.conn_B:
                self.conn_B.shutdown(socket.SHUT_RDWR)
                self.conn_B.close()
        except OSError:
            pass

        if self.ppool:
            self.ppool.terminate()
            self.ppool.join()
