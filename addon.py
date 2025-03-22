# -*- coding: utf-8 -*-
# Copyright (c) 2024 joaosagrath <joaosagrath@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# PhotoSets main script file.

# --- Modules/packages in this plugin ---
import resources.main as main

# --- Python standard library ---
import sys

# -------------------------------------------------------------------------------------------------
# main()
# -------------------------------------------------------------------------------------------------
# Put the main bulk of the code in files inside /resources/, which is a package directory.
# This way, the Python interpreter will precompile them into bytecode (files PYC/PYO) so
# loading time is faster compared to loading PY files.
# See http://www.network-theory.co.uk/docs/pytut/CompiledPythonfiles.html
main.Main().run_plugin(sys.argv)
