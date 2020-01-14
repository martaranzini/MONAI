# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from .utils.moduleutils import load_submodules, loadSubmodules

__copyright__ = "(c) 2020 MONAI Consortium"
__version__tuple__ = (0, 0, 1)
__version__ = "%i.%i.%i" % (__version__tuple__)

__basedir__ = os.path.dirname(__file__)

load_submodules(sys.modules[__name__], False)  # load directory modules only, skip loading individual files
load_submodules(sys.modules[__name__], True)  # load all modules, this will trigger all export decorations