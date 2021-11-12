import sys
from austin_heller_repo.version_controlled_containerized_python_manager import VersionControlledContainerizedPythonManager, DockerContainerInstanceTimeoutException
from austin_heller_repo.git_manager import GitManager
import tempfile
from typing import List
import json
from datetime import datetime

git_url = None  # type: str
script_file_path = None  # type: str
script_arguments = []  # type: List[str]
timeout_seconds = None  # type: float

arg_index = 1
while arg_index < len(sys.argv):
	if sys.argv[arg_index] == "-g":
		if git_url is not None:
			raise Exception(f"Already provided git url. Have \"{git_url}\", found \"{sys.argv[arg_index]}\".")
		arg_index += 1
		git_url = sys.argv[arg_index]
	elif sys.argv[arg_index] == "-s":
		if script_file_path is not None:
			raise Exception(f"Already provided script file path. Have \"{script_file_path}\", found \"{sys.argv[arg_index]}\".")
		arg_index += 1
		script_file_path = sys.argv[arg_index]
	elif sys.argv[arg_index] == "-sa":
		arg_index += 1
		script_arguments.append(sys.argv[arg_index])
	elif sys.argv[arg_index] == "-t":
		if timeout_seconds is not None:
			raise Exception(f"Already provided timeout seconds. Have \"{timeout_seconds}\", found \"{sys.argv[arg_index]}\".")
		arg_index += 1
		timeout_seconds = float(sys.argv[arg_index])
	else:
		raise Exception(f"Failed to parse commandline argument: \"{sys.argv[arg_index]}\".")
	arg_index += 1

temp_directory = tempfile.TemporaryDirectory()

git_manager = GitManager(
	git_directory_path=temp_directory.name
)

vccpm = VersionControlledContainerizedPythonManager(
	git_manager=git_manager
)

output = {
	"data": None,
	"exception": None
}

try:

	with vccpm.run_python_script(
		git_repo_clone_url=git_url,
		script_file_path=script_file_path,
		script_arguments=script_arguments,
		timeout_seconds=timeout_seconds
	) as vccpi:

		start_time = datetime.utcnow()
		vccpi.wait()
		end_time = datetime.utcnow()
		child_output = json.loads(vccpi.get_output())
		output["data"] = [
			child_output["data"],
			git_url,
			script_file_path,
			script_arguments,
			(end_time - start_time).total_seconds()
		]
		output["exception"] = child_output["exception"]
except DockerContainerInstanceTimeoutException as ex:
	output["exception"] = str(ex)

print(json.dumps(output))
