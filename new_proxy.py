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

import multiprocessing
import socket

from distributions import Distribution

multiprocessing.allow_connection_pickling()


class SimplexRelay(multiprocessing.Process):
    def __init__(self,
                 conn_a: socket.SocketType,
                 conn_b: socket.SocketType,
                 delay_dist: Distribution):
        super().__init__(daemon=True)
        self.conn_a = conn_a
        self.conn_b = conn_b
        self.delay_dist = delay_dist

        self.shutdown_signal = multiprocessing.Event()
        self.shutdown_signal.clear()


