from __future__ import annotations
from typing import List, Tuple, Dict
import docker
from docker.models.containers import Container
from docker.client import DockerClient
import re
import io
import tarfile
import os


class DockerContainerInstance():

	def __init__(self, *, image_name: str, container_name: str, docker_client: DockerClient, docker_container: Container):

		self.__image_name = image_name
		self.__container_name = container_name
		self.__docker_client = docker_client
		self.__docker_container = docker_container

		self.__stdout = None

	def get_stdout(self) -> str:
		logs = self.__docker_container.logs()
		if logs != b"":
			if self.__stdout is None:
				self.__stdout = b""
			self.__stdout += logs
		if self.__stdout is None:
			return None
		else:
			line = self.__stdout
			self.__stdout = None
			return line

	def execute_command(self, *, command: str):
		lines = self.__docker_container.exec_run(command, stderr=True, stdout=True)
		if "exec failed" in str(lines) or "409 Client Error" in str(lines):
			raise Exception(f"execute_command failed: {lines}")
		for line in lines:
			if line != 0:
				if self.__stdout is None:
					self.__stdout = b""
				self.__stdout += line

	def copy_file(self, *, source_file_path: str, destination_file_path: str):
		stream = io.BytesIO()
		with tarfile.open(fileobj=stream, mode="w|") as tar, open(source_file_path, "rb") as source_file_handle:
			tar_info = tar.gettarinfo(fileobj=source_file_handle)
			tar_info.name = os.path.basename(source_file_path)
			tar.addfile(tar_info, source_file_handle)
		self.__docker_container.put_archive(destination_file_path, stream.getvalue())

	def stop(self):
		if self.__docker_container is None:
			raise Exception(f"Already stopped instance.")
		else:
			self.__docker_container.stop()
			self.__docker_container.remove()
			self.__docker_client.images.remove(self.__image_name)
			self.__docker_container = None


class DockerManager():

	def __init__(self, *, dockerfile_directory_path: str):

		self.__dockerfile_directory_path = dockerfile_directory_path

		self.__docker_client = docker.from_env()
		self.__image_name = None  # type: str
		self.__container_name = None  # type: str

	def start(self, *, image_name: str, container_name: str) -> DockerContainerInstance:

		if re.search(r"\s", image_name):
			raise Exception(f"Image name cannot contain whitespace.")
		elif re.search(r"\s", container_name):
			raise Exception(f"Container name cannot contain whitespace.")
		else:
			self.__docker_client.images.build(
				path=self.__dockerfile_directory_path,
				tag=image_name,
				rm=True
			)
			docker_container = self.__docker_client.containers.run(
				image=image_name,
				name=container_name,
				detach=True,
				stdout=True,
				stderr=True
			)
			docker_container_instance = DockerContainerInstance(
				image_name=image_name,
				container_name=container_name,
				docker_client=self.__docker_client,
				docker_container=docker_container
			)
			return docker_container_instance

	def dispose(self):
		self.__docker_client.close()
