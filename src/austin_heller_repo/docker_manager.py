from __future__ import annotations
from typing import List, Tuple, Dict
import docker
from docker.models.containers import Container


class DockerContainerInstance():

	def __init__(self, *, image_name: str, container_name: str, docker_container: Container):

		self.__image_name = image_name
		self.__container_name = container_name
		self.__docker_container = docker_container

	def execute_command(self, *, command: str):
		self.__docker_container.exec_run(command)

	def stop(self):
		if self.__docker_container is None:
			raise Exception(f"Already stopped instance.")
		else:
			self.__docker_container.stop()
			self.__docker_container = None


class DockerManager():

	def __init__(self, *, dockerfile_directory_path: str):

		self.__dockerfile_directory_path = dockerfile_directory_path

		self.__docker_client = docker.from_env()
		self.__image_name = None  # type: str
		self.__container_name = None  # type: str

	def start(self, *, image_name: str, container_name: str) -> DockerContainerInstance:
		self.__docker_client.images.build(
			path=self.__dockerfile_directory_path,
			tag=image_name
		)
		docker_container = self.__docker_client.containers.run(
			image=image_name,
			name=container_name,
			detach=True
		)
		docker_container_instance = DockerContainerInstance(
			image_name=image_name,
			container_name=container_name,
			docker_container=docker_container
		)
		return docker_container_instance
