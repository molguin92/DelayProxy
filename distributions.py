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

import numpy as np
from functools import partial


class Distribution:
    """
    Interface for statistical distributions
    """

    def sample(self) -> float:
        pass


class ConstantDistribution(Distribution):
    def __init__(self, constant: float):
        super().__init__()
        self.constant = constant

    def sample(self) -> float:
        return self.constant


class PseudoNormalDistribution(Distribution):
    def __init__(self, mean: float, std_dev: float,
                 strictly_positive: bool = False):
        super().__init__()
        self.dist = partial(np.random.normal, loc=mean, scale=std_dev)
        self.positive = strictly_positive

    def sample(self) -> float:
        if self.positive:
            return max(self.dist(), 0.0)
        else:
            return self.dist()


class ExponentialDistribution(Distribution):
    def __init__(self, scale: float):
        super().__init__()
        self.dist = partial(np.random.exponential, scale=scale)

    def sample(self) -> float:
        return self.dist()
