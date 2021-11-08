import unittest
from src.austin_heller_repo.docker_manager import DockerManager, DockerContainerInstance
import tempfile
import docker.models.images
import docker.errors
import time
from datetime import datetime


class DockerManagerTest(unittest.TestCase):

	def setUp(self):

		docker_client = docker.from_env()

		image_names = [
			"helloworld",
			"multiple_stdout",
			"waits_five_seconds",
			"print_every_second_for_ten_seconds"
		]

		for image_name in image_names:

			try:
				docker_client.containers.get(f"test_{image_name}_container").remove()
			except Exception as ex:
				pass

			try:
				docker_client.images.remove(
					image=f"test_{image_name}_image"
				)
			except Exception as ex:
				pass

		docker_client.close()

	def test_initialize_docker_manager(self):

		temp_directory = tempfile.TemporaryDirectory()

		docker_manager = DockerManager(
			dockerfile_directory_path=temp_directory.name
		)

		self.assertIsNotNone(docker_manager)

		temp_directory.cleanup()

		docker_manager.dispose()

	def test_initialize_docker_manager_start_failed(self):

		temp_directory = tempfile.TemporaryDirectory()

		docker_manager = DockerManager(
			dockerfile_directory_path=temp_directory.name
		)

		self.assertIsNotNone(docker_manager)

		with self.assertRaises(docker.errors.APIError) as ex:
			docker_container_instance = docker_manager.start(
				image_name="test_empty_image",
				container_name="test_empty_container"
			)

		temp_directory.cleanup()

		self.assertIn("Cannot locate specified Dockerfile: Dockerfile", str(ex.exception))

		docker_manager.dispose()

	def test_whitespace_in_image_name_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		with self.assertRaises(Exception) as ex:
			docker_container_instance = docker_manager.start(
				image_name="test helloworld image",
				container_name="test_helloworld_container"
			)

		self.assertIn("Image name cannot contain whitespace.", str(ex.exception))

		docker_manager.dispose()

	def test_whitespace_in_container_name_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		with self.assertRaises(Exception) as ex:
			docker_container_instance = docker_manager.start(
				image_name="test_helloworld_image",
				container_name="test helloworld container"
			)

		self.assertIn("Container name cannot contain whitespace.", str(ex.exception))

		docker_manager.dispose()

	def test_start_helloworld_docker_image(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_helloworld_image",
			container_name="test_helloworld_container"
		)

		self.assertIsNotNone(docker_container_instance)

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_helloworld_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_helloworld_image",
			container_name="test_helloworld_container"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_helloworld_docker_image_ls_command_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_helloworld_image",
			container_name="test_helloworld_container"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

		with self.assertRaises(Exception) as ex:
			docker_container_instance.execute_command(
				command="ls"
			)

		#self.assertIn("execute_command failed: ", str(ex.exception))
		self.assertRegex(str(ex.exception), "Container [a-f0-9]+ is not running")

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_waits_five_seconds_docker_image_ls_command(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds"
		)

		print(f"time 0: {datetime.utcnow()}")

		docker_container_instance = docker_manager.start(
			image_name="test_waits_five_seconds_image",
			container_name="test_waits_five_seconds_container"
		)

		print(f"time 1: {datetime.utcnow()}")

		self.assertIsNotNone(docker_container_instance)

		stdout = docker_container_instance.get_stdout()

		print(f"time 2: {datetime.utcnow()}")

		#self.assertEqual(b"", stdout)
		self.assertIsNone(stdout)

		docker_container_instance.execute_command(
			command="ls"
		)

		print(f"time 3: {datetime.utcnow()}")

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		print(f"time 4: {datetime.utcnow()}")

		print(f"stdout: {stdout}")

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_multiple_stdout_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/multiple_stdout"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_multiple_stdout_image",
			container_name="test_multiple_stdout_container"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"first\nsecond\n", stdout)

		docker_container_instance.stop()

		docker_manager.dispose()

	def _test_copying_file_to_container(self):

		temp_file = tempfile.TemporaryFile()

		temp_file.write("test")
		temp_file.flush()

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_helloworld_image",
			container_name="test_helloworld_container"
		)

		self.assertIsNotNone(docker_container_instance)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

		docker_container_instance.copy_file(
			source_file_path=temp_file.name,
			destination_file_path="test.txt"
		)

		docker_container_instance.execute_command(
			command="ls"
		)

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_print_every_second_for_ten_seconds_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/print_every_second_for_ten_seconds"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_print_every_second_for_ten_seconds_image",
			container_name="test_print_every_second_for_ten_seconds_container"
		)

		self.assertIsNotNone(docker_container_instance)

		all_stdout = b""

		for index in range(10):

			time.sleep(1)

			stdout = docker_container_instance.get_stdout()

			if stdout is not None:
				all_stdout += stdout

		self.assertEqual(b"0\n1\n2\n3\n4\n5\n6\n7\n8\n9\n", all_stdout)

		docker_container_instance.stop()

		docker_manager.dispose()

	def test_start_print_every_second_for_ten_seconds_docker_image_get_stdout_with_echo(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/print_every_second_for_ten_seconds"
		)

		docker_container_instance = docker_manager.start(
			image_name="test_print_every_second_for_ten_seconds_image",
			container_name="test_print_every_second_for_ten_seconds_container"
		)

		self.assertIsNotNone(docker_container_instance)

		all_stdout = b""

		for index in range(10):

			time.sleep(1)

			stdout = docker_container_instance.get_stdout()

			if stdout is not None:
				all_stdout += stdout

			if index == 5:
				docker_container_instance.execute_command(
					command=f"echo test{index}"
				)

		self.assertEqual(b"0\n1\n2\n3\n4\n5\ntest5\n6\n7\n8\n9\n", all_stdout)

		docker_container_instance.stop()

		docker_manager.dispose()
