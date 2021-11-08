import unittest
from src.austin_heller_repo.docker_manager import DockerManager, DockerContainerInstance
import tempfile
import docker.models.images
import docker.errors
import time


class DockerManagerTest(unittest.TestCase):

	def setUp(self):

		docker_client = docker.from_env()

		image_names = [
			"helloworld",
			"multiple_stdout"
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

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

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

		time.sleep(1)

		self.assertIsNotNone(docker_container_instance)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"first\nsecond\n", stdout)

		docker_container_instance.stop()

		docker_manager.dispose()
