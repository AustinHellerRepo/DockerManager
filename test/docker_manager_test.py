import unittest
from src.austin_heller_repo.docker_manager import DockerManager, DockerContainerInstance, DockerContainerInstanceAlreadyExistsException, DockerContainerAlreadyRemovedException
import tempfile
import docker.models.images
import docker.errors
import time
from datetime import datetime
import os
import gc
import json


class DockerManagerTest(unittest.TestCase):

	def setUp(self):

		docker_client = docker.from_env()
		api_client = docker.APIClient(base_url="unix://var/run/docker.sock")

		image_names = [
			"helloworld",
			"multiple_stdout",
			"waits_five_seconds",
			"print_every_second_for_ten_seconds",
			"contains_script",
			"helloworld_2",
			"contains_script_2",
			"spawns_container"
		]

		for image_name in image_names:

			try:
				docker_client.containers.get(f"test_{image_name}").kill()
			except Exception as ex:
				pass

			try:
				docker_client.containers.get(f"test_{image_name}").remove()
			except Exception as ex:
				pass

			try:
				api_client.remove_container(f"test_{image_name}", force=True)
			except Exception as ex:
				pass

			try:
				docker_client.images.remove(
					image=f"test_{image_name}"
				)
			except Exception as ex:
				pass

			try:
				api_client.remove_image(f"test_{image_name}", force=True)
			except Exception as ex:
				pass

		docker_client.close()

	def test_initialize_docker_manager(self):

		temp_directory = tempfile.TemporaryDirectory()

		docker_manager = DockerManager(
			dockerfile_directory_path=temp_directory.name,
			is_docker_socket_needed=False
		)

		self.assertIsNotNone(docker_manager)

		temp_directory.cleanup()

		docker_manager.dispose()

	def test_initialize_docker_manager_start_failed(self):

		temp_directory = tempfile.TemporaryDirectory()

		docker_manager = DockerManager(
			dockerfile_directory_path=temp_directory.name,
			is_docker_socket_needed=False
		)

		self.assertIsNotNone(docker_manager)

		with self.assertRaises(docker.errors.APIError) as ex:
			docker_container_instance = docker_manager.start(
				name="test_empty"
			)

		temp_directory.cleanup()

		self.assertIn("Cannot locate specified Dockerfile: Dockerfile", str(ex.exception))

		docker_manager.dispose()

	def test_whitespace_in_name_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld",
			is_docker_socket_needed=False
		)

		with self.assertRaises(Exception) as ex:
			docker_container_instance = docker_manager.start(
				name="test helloworld"
			)

		self.assertIn("Name cannot contain whitespace.", str(ex.exception))

		docker_manager.dispose()

	def test_start_helloworld_docker_image(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_helloworld"
		)

		self.assertIsNotNone(docker_container_instance)

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_helloworld_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_helloworld"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_helloworld_docker_image_ls_command_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_helloworld"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"Hello world!\n", stdout)

		# this used to raise an exception, but now it spawns a duplicate container and runs the command
		docker_container_instance.execute_command(
			command="ls"
		)

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_waits_five_seconds_docker_image_ls_command(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds",
			is_docker_socket_needed=False
		)

		print(f"time 0: {datetime.utcnow()}")

		docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
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
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_multiple_stdout_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/multiple_stdout",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_multiple_stdout"
		)

		self.assertIsNotNone(docker_container_instance)

		time.sleep(1)

		stdout = docker_container_instance.get_stdout()

		self.assertEqual(b"first\nsecond\n", stdout)

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_copying_file_to_container(self):

		temp_file = tempfile.NamedTemporaryFile(delete=False)

		temp_file.write(b"test")
		temp_file.flush()
		temp_file.close()

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
		)

		self.assertIsNotNone(docker_container_instance)

		docker_container_instance.copy_file(
			source_file_path=temp_file.name,
			destination_directory_path="/"
		)

		file_name = os.path.basename(temp_file.name)

		os.unlink(temp_file.name)

		docker_container_instance.execute_command(
			command="ls"
		)

		stdout = docker_container_instance.get_stdout()

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

		self.assertIn(file_name, stdout.decode())

	def test_start_print_every_second_for_ten_seconds_docker_image_get_stdout(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/print_every_second_for_ten_seconds",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_print_every_second_for_ten_seconds"
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
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_print_every_second_for_ten_seconds_docker_image_get_stdout_with_echo(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/print_every_second_for_ten_seconds",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_print_every_second_for_ten_seconds"
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

		self.assertIn(all_stdout, [b"0\n1\n2\n3\n4\n5\ntest5\n6\n7\n8\n9\n", b"0\n1\n2\n3\n4\ntest5\n5\n6\n7\n8\n9\n"])

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_wait_for_container_to_complete_five_seconds(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds",
			is_docker_socket_needed=False
		)

		before_start_datetime = datetime.utcnow()

		docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
		)

		before_wait_datetime = datetime.utcnow()

		docker_container_instance.wait()

		end_datetime = datetime.utcnow()

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()

		first_difference_seconds = (before_wait_datetime - before_start_datetime).total_seconds()

		second_difference_seconds = (end_datetime - before_wait_datetime).total_seconds()

		print(f"first_difference_seconds: {first_difference_seconds}")
		print(f"second_difference_seconds: {second_difference_seconds}")

		self.assertGreater(second_difference_seconds, first_difference_seconds)
		self.assertGreater(second_difference_seconds, 5)

	def test_wait_for_container_to_complete_five_seconds_already_completed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds",
			is_docker_socket_needed=False
		)

		before_start_datetime = datetime.utcnow()

		docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
		)

		time.sleep(6)

		before_wait_datetime = datetime.utcnow()

		docker_container_instance.wait()

		end_datetime = datetime.utcnow()

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()

		first_difference_seconds = (before_wait_datetime - before_start_datetime).total_seconds()

		second_difference_seconds = (end_datetime - before_wait_datetime).total_seconds()

		print(f"first_difference_seconds: {first_difference_seconds}")
		print(f"second_difference_seconds: {second_difference_seconds}")

		self.assertGreater(1, second_difference_seconds)

	def test_contains_script(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/contains_script",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_contains_script"
		)

		time.sleep(1)

		first_stdout = docker_container_instance.get_stdout()
		self.assertEqual(None, first_stdout)

		for index in range(4):

			docker_container_instance.execute_command(
				command=f"python start.py {index}"
			)

			time.sleep(1)

			second_stdout = docker_container_instance.get_stdout()
			self.assertEqual(f"{index}\n".encode(), second_stdout)

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()

	def test_start_print_every_second_for_ten_seconds_docker_image_get_stdout_with_echo_try_start_second_container_failed(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/print_every_second_for_ten_seconds",
			is_docker_socket_needed=False
		)

		docker_container_name = "test_print_every_second_for_ten_seconds"

		docker_container_instance = docker_manager.start(
			name=docker_container_name
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
			elif index == 7:
				with self.assertRaises(DockerContainerInstanceAlreadyExistsException):
					second_docker_container = docker_manager.start(
						name=docker_container_name
					)

		self.assertIn(all_stdout, [b"0\n1\n2\n3\n4\n5\ntest5\n6\n7\n8\n9\n", b"0\n1\n2\n3\n4\ntest5\n5\n6\n7\n8\n9\n"])

		docker_container_instance.stop()
		docker_container_instance.remove()

		docker_manager.dispose()

	def test_start_container_stop_container_start_different_container_object_try_start_first_container_object(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/waits_five_seconds",
			is_docker_socket_needed=False
		)

		first_docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
		)

		first_docker_container_instance.stop()
		first_docker_container_instance.remove()

		second_docker_container_instance = docker_manager.start(
			name="test_waits_five_seconds"
		)

		with self.assertRaises(DockerContainerAlreadyRemovedException):
			first_docker_container_instance.start()

	def test_duplicate_container(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/contains_script",
			is_docker_socket_needed=False
		)

		times = []

		times.append(datetime.utcnow())

		first_docker_container_instance = docker_manager.start(
			name="test_contains_script"
		)

		times.append(datetime.utcnow())

		first_docker_container_instance.wait()

		times.append(datetime.utcnow())

		first_docker_container_instance.stop()

		times.append(datetime.utcnow())

		first_stdout = first_docker_container_instance.get_stdout()

		print(f"first_stdout: {first_stdout}")

		times.append(datetime.utcnow())

		second_docker_container_instance = first_docker_container_instance.duplicate_container(
			name="test_contains_script_2",
			override_entrypoint_arguments=["python", "start.py", "test"]
		)

		times.append(datetime.utcnow())

		second_docker_container_instance.start()

		times.append(datetime.utcnow())

		second_docker_container_instance.wait()

		times.append(datetime.utcnow())

		second_docker_container_instance.stop()

		times.append(datetime.utcnow())

		second_stdout = second_docker_container_instance.get_stdout()

		print(f"second_stdout: {second_stdout}")

		times.append(datetime.utcnow())

		print(f"times: {times}")

		first_docker_container_instance.remove()
		second_docker_container_instance.remove()
		docker_manager.dispose()

		self.assertEqual(b"test\n", second_stdout)

	def test_sequential_commands(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/helloworld",
			is_docker_socket_needed=False
		)

		docker_container_instance = docker_manager.start(
			name="test_helloworld"
		)

		docker_container_instance.wait()

		docker_container_instance.execute_command(
			command="mkdir test_directory"
		)

		docker_container_instance.execute_command(
			command="ls"
		)

		output = docker_container_instance.get_stdout()

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()

		self.assertEqual(b"Hello world!\nbin\nboot\ndev\netc\nhome\nlib\nlib32\nlib64\nlibx32\nmedia\nmnt\nopt\nproc\nroot\nrun\nsbin\nsrv\nsys\ntest_directory\ntmp\nusr\nvar\n", output)

	def test_spawn_container(self):

		docker_manager = DockerManager(
			dockerfile_directory_path="./dockerfiles/spawns_container",
			is_docker_socket_needed=True
		)

		docker_container_instance = docker_manager.start(
			name="test_spawns_container"
		)

		git_url = "https://github.com/AustinHellerRepo/TestDockerTimeDelay.git"
		script_file_path = "start.py"

		docker_container_instance.execute_command(
			command=f"python start.py -g {git_url} -s {script_file_path} -t 20"
		)

		docker_container_instance.wait()

		output = docker_container_instance.get_stdout()

		output_json = json.loads(output.decode())

		self.assertEqual(0, len(output_json["data"][0]))
		self.assertEqual(git_url, output_json["data"][1])
		self.assertEqual(script_file_path, output_json["data"][2])

		print(f"Execution time: {output_json['data'][4]}")

		docker_container_instance.stop()
		docker_container_instance.remove()
		docker_manager.dispose()
