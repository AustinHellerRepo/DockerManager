from __future__ import annotations
from typing import List, Tuple, Dict
import docker
from docker.models.containers import Container
from docker.models.images import Image
from docker.client import DockerClient
from docker.errors import APIError
import re
import io
import tarfile
import os
from datetime import datetime
import uuid
import time


class DockerContainerInstanceAlreadyExistsException(Exception):

	def __init__(self, *args: object):
		super().__init__(*args)


class FailedToFindContainerException(Exception):

	def __init__(self, *args: object):
		super().__init__(*args)


class DockerContainerAlreadyRemovedException(Exception):

	def __init__(self, *args: object):
		super().__init__(*args)


class DockerContainerInstance():

	def __init__(self, *, name: str, docker_client: DockerClient, docker_container: Container):

		self.__name = name
		self.__docker_client = docker_client
		self.__docker_container = docker_container

		self.__stdout = None
		self.__docker_container_logs_sent_length = 0

	def get_stdout(self) -> bytes:
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		logs = self.__docker_container.logs()
		if logs != b"":
			sending_length = len(logs)
			unsent_logs = logs[self.__docker_container_logs_sent_length:sending_length]
			self.__docker_container_logs_sent_length = sending_length
			if self.__stdout is None:
				self.__stdout = b""
			self.__stdout += unsent_logs
		if self.__stdout is None:
			return None
		else:
			line = self.__stdout
			self.__stdout = None
			return line

	def duplicate_container(self, *, name: str, override_entrypoint_arguments:List[str] = None) -> DockerContainerInstance:
		duplicate_docker_image = self.__docker_container.commit(
			repository=name
		)  # type: Image

		if override_entrypoint_arguments is not None and len(override_entrypoint_arguments) != 0:
			concat_entrypoint_arguments = ""
			for entrypoint_argument_index, entrypoint_argument in enumerate(override_entrypoint_arguments):
				if entrypoint_argument_index != 0:
					concat_entrypoint_arguments += " "
				concat_entrypoint_arguments += f"{entrypoint_argument}"

			duplicate_docker_container = self.__docker_client.containers.create(
				image=duplicate_docker_image,
				name=name,
				detach=True,
				command=concat_entrypoint_arguments
			)
		else:
			duplicate_docker_container = self.__docker_client.containers.create(
				image=duplicate_docker_image
			)
		duplicate_docker_container_instance = DockerContainerInstance(
			name=name,
			docker_client=self.__docker_client,
			docker_container=duplicate_docker_container
		)
		return duplicate_docker_container_instance

	def execute_command(self, *, command: str):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		is_successful = False
		try:
			lines = self.__docker_container.exec_run(command, stderr=True, stdout=True)
			is_successful = True
		except APIError as ex:
			if "409 Client Error" in str(ex) and " is not running" in str(ex):
				docker_clone_uuid = f"duplicate_{str(uuid.uuid4()).lower()}"
				duplicate_docker_container = self.duplicate_container(
					name=docker_clone_uuid,
					override_entrypoint_arguments=[command]
				)
				duplicate_docker_container.start()
				duplicate_docker_container.wait()
				output = duplicate_docker_container.get_stdout()
				duplicate_docker_container.stop()
				duplicate_docker_container.remove()

				if self.__stdout is None:
					self.__stdout = output
				else:
					self.__stdout += output
			else:
				raise ex
		if is_successful:
			for line in lines:
				if isinstance(line, int):
					pass
				else:
					if self.__stdout is None:
						self.__stdout = b""
					print(f"line: {line}")
					self.__stdout += line

	def copy_file(self, *, source_file_path: str, destination_directory_path: str):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		stream = io.BytesIO()
		with tarfile.open(fileobj=stream, mode="w|") as tar, open(source_file_path, "rb") as source_file_handle:
			tar_info = tar.gettarinfo(fileobj=source_file_handle)
			tar_info.name = os.path.basename(source_file_path)
			tar.addfile(tar_info, source_file_handle)
		self.__docker_container.put_archive(destination_directory_path, stream.getvalue())

	def wait(self):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		self.__docker_container.wait()

	def is_running(self) -> bool:
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		return self.__docker_container.status in ["running", "created"]

	def stop(self):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		if self.is_running():
			self.__docker_container.stop()
			#print(f"docker_manager: stop: self.__docker_container.status: {self.__docker_container.status}")

	def start(self):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container was previously removed.")
		#print(f"docker_manager: start: self.is_running(): {self.is_running()}")
		self.__docker_container.start()

	def remove(self):
		if self.__docker_container is None:
			raise DockerContainerAlreadyRemovedException(f"Docker container already removed.")
		self.stop()
		self.__docker_container.remove()
		self.__docker_client.images.remove(self.__name)
		self.__docker_container = None


class DockerManager():

	def __init__(self, *, dockerfile_directory_path: str):

		self.__dockerfile_directory_path = dockerfile_directory_path

		self.__docker_client = docker.from_env()

	def is_image_exists(self, *, name: str) -> bool:

		images = self.__docker_client.images.list()  # type: List[Image]
		for image in images:
			if f"{name}:latest" in image.tags:
				return True
		return False

	def is_container_exists(self, *, name: str) -> bool:

		containers = self.__docker_client.containers.list()  # type: List[Container]
		for container in containers:
			if container.name == name:
				return True
		return False

	def get_existing_docker_container_instance_from_name(self, *, name: str) -> DockerContainerInstance:
		if not self.is_container_exists(
			name=name
		):
			raise FailedToFindContainerException(f"Failed to find container based on name \"{name}\".")
		containers = self.__docker_client.containers()  # type: List[Container]
		found_container = None
		for container in containers:
			if container.name == name:
				found_container = container
				break
		if found_container is None:
			raise FailedToFindContainerException(f"Unexpected missing container after already finding it by name \"{name}\".")
		docker_container_instance = DockerContainerInstance(
			name=name,
			docker_client=self.__docker_client,
			docker_container=found_container
		)
		return docker_container_instance

	def start(self, *, name: str) -> DockerContainerInstance:

		if re.search(r"\s", name):
			raise Exception(f"Name cannot contain whitespace.")
		else:
			if self.is_image_exists(
				name=name
			) or self.is_container_exists(
				name=name
			):
				raise DockerContainerInstanceAlreadyExistsException(f"Cannot start container with the same name.")

			self.__docker_client.images.build(
				path=self.__dockerfile_directory_path,
				tag=name,
				rm=True
			)
			docker_container = self.__docker_client.containers.run(
				image=name,
				name=name,
				detach=True,
				stdout=True,
				stderr=True
			)
			docker_container_instance = DockerContainerInstance(
				name=name,
				docker_client=self.__docker_client,
				docker_container=docker_container
			)
			return docker_container_instance

	def dispose(self):
		self.__docker_client.close()
