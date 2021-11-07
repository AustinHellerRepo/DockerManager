from __future__ import annotations
from typing import List, Tuple, Dict


class DockerManager():

	def __init__(self, *, dockerfile_directory_path: str):

		self.__dockerfile_directory_path = dockerfile_directory_path

	def start(self):
		raise NotImplementedError()

	def execute_command(self, *, command: str):
		raise NotImplementedError()

	def stop(self):
		raise NotImplementedError()
