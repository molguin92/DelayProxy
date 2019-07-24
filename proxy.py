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
from multiprocessing import Event, Pool
from multiprocessing.pool import AsyncResult
from typing import Optional, Union

from logzero import logger

from distributions import Distribution


def pool_init(shutdown_signal: Event):
    global shutdown_event
    shutdown_event = shutdown_signal


def relay(conn_A: socket.SocketType,
          conn_B: socket.SocketType,
          delay_dist: Distribution,
          chunk_size: int = 4096) -> None:
    logger.debug('Relaying!')
    try:
        while not shutdown_event.is_set():
            # read from A, wait X time, send to B
            data = conn_A.recv(chunk_size)
            time.sleep(delay_dist.sample())
            conn_B.sendall(data)
    except socket.error as e:
        logger.warning(e)
        pass
    except Exception as e:
        logger.exception(e)


class DelayProxy:
    SHUTDOWN_TIMEOUT = 3

    __relay = staticmethod(relay)

    def __init__(self,
                 listen_host: str,
                 listen_port: int,
                 connect_host: str,
                 connect_port: int,
                 delay_dist: Optional[Distribution] = None,
                 chunk_size: int = 4096):
        super().__init__()

        logger.info(f'Setting up relay from '
                    f'{listen_host}:{listen_port} to '
                    f'{connect_host}:{connect_port}')

        if delay_dist:
            logger.info(f'Setting delay distribution to: {delay_dist}')

        self.listen_addr = (listen_host, listen_port)
        self.connect_addr = (connect_host, connect_port)
        self.shutdown_signal = Event()
        self.chunk_size = chunk_size

        self.delay_dist = delay_dist
        self.result_AtoB: Optional[AsyncResult] = None
        self.result_BtoA: Optional[AsyncResult] = None
        self.ppool: Optional[Pool] = None
        self.conn_A: Optional[socket.SocketType] = None
        self.conn_B: Optional[socket.SocketType] = None

    def set_distribution(self, distribution: Distribution):
        if not self.shutdown_signal.is_set():
            logger.info(f'Setting delay distribution to: {distribution}')
            self.delay_dist = distribution

    def __setup(self) -> None:
        l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        l_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logger.info('Listening on {}:{}'.format(*self.listen_addr))
        l_sock.bind(self.listen_addr)
        l_sock.listen(0)
        self.conn_A, addr_A = l_sock.accept()
        logger.info('Got connection from {}:{}'.format(*addr_A))

        # self.log.info(f'Accepted connection from {addr_A}')

        logger.info('Connecting to {}:{}...'.format(*self.connect_addr))
        self.conn_B = socket.create_connection(self.connect_addr)
        logger.info('Connected. Ready to relay from '
                    '{}:{} to {}:{}'.format(*addr_A, *self.connect_addr))
        # self.log.info(f'Connected to {self.connect_addr}')

    def start(self) -> None:
        logger.info('Initializing relay.')
        if self.delay_dist is None:
            raise RuntimeError('Delay distribution for proxy is unset!')

        self.__setup()
        logger.debug('Setting up process pool for full-duplex relaying.')
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
        logger.warning('Shutting down relay!')
        self.shutdown_signal.set()
        try:
            if self.conn_A:
                logger.debug('Shutting down connection A...')
                self.conn_A.shutdown(socket.SHUT_RDWR)
                self.conn_A.close()
                logger.debug('Connection A shut down.')
        except OSError:
            logger.warning('Error shutting down incoming side!')
            pass

        try:
            if self.conn_B:
                logger.debug('Shutting down connection B...')
                self.conn_B.shutdown(socket.SHUT_RDWR)
                self.conn_B.close()
                logger.debug('Connection B shut down.')
        except OSError:
            logger.warning('Error shutting down outgoing side!')
            pass

        if self.ppool:
            logger.debug('Terminating process pool...')
            self.ppool.terminate()
            self.ppool.join()
            logger.debug('Process pool terminated.')

        self.shutdown_signal.clear()
