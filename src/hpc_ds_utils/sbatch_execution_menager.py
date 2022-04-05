import logging
import os
import pathlib
import pickle
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import List, Union

from jinja2 import Environment

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def generate_sbatch_scripts(conda_env: str = None,
                            command: str = None,
                            job_name: str = None,
                            user: str = None,
                            nodes: str = None,
                            ntasks: int = None,
                            cpus_per_task: int = None,
                            mem: str = None,
                            time: str = None,
                            output: str = None) -> str:
    """
    function to generate a sbatch script to be submitted with sbatch in slurm
    Args:
        conda_env: name of the conda env to be used
        command: command to be executed
        job_name: name of the job to be executed
        user: user
        nodes: nodes to be used
        ntasks: number of tasks
        cpus_per_task: number of cpus per task
        mem: memory to be allocated
        time: time limit
        output: slurm output dir

    Returns:
        string representing the sbatch script to be executed in slurm with sbatch
    """
    template = """#!/bin/bash
{% if job_name %}
#SBATCH --job-name={{ job_name }}
{% endif %}
{% if user %}
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user={{ user }}
{% endif %}
{% if nodes %}
#SBATCH --nodes={{ nodes }}
{% endif %}
{% if ntasks %}
#SBATCH --ntasks={{ ntasks }}
{% endif %}
{% if cpus_per_task %}
#SBATCH --cpus-per-task={{ cpus_per_task }}
{% endif %}
#SBATCH --distribution=cyclic:cyclic
{% if mem %}
#SBATCH --mem={{ mem }}
{% endif %}
{% if time %}
#SBATCH --time={{ time }}
{% endif %}
{% if output and job_name %}
#SBATCH --chdir={{ output }}/{{ job_name }}/
{% endif %}
{% if job_name %}
#SBATCH --output={{ job_name }}_%j.log
{% endif %}
{% if job_name %}
#SBATCH --error={{ job_name }}_%j.err
{% endif %}
# ------------------------------ COMMAND SECTION -------------------------------------------
{% if conda_env %}
source ~/miniconda3/etc/profile.d/conda.sh
conda activate {{ conda_env }}
{% endif %}
{{ cmd }}
{% if conda_env %}
conda deactivate
{% endif %}
      """
    dict_sbatch_params = dict(
        conda_env=conda_env,
        cmd=command,
        job_name=job_name,
        user=user,
        ntasks=ntasks,
        nodes=nodes,
        cpus_per_task=cpus_per_task,
        mem=mem,
        time=time,
        output=output
    )

    path = os.path.join(output, job_name)
    env = Environment(trim_blocks=True)
    log.info(f"rendering sbatch scripts at path: {str(pathlib.Path(path).resolve())}")
    if not os.path.exists(path):
        os.makedirs(path)
    return env.from_string(template).render(**dict_sbatch_params)


class SbatchJobExecutionManager:
    """
    class to execute slurm jobs using sbatch
    """
    path_to_registry = str(
        Path(__file__).resolve() / "command_registry_sbatch.pkl")
    if not Path(path_to_registry).parent.exists():
        os.makedirs(Path(path_to_registry).parent)
    command_registry = []

    def __init__(self,
                 conda_env: str = None,
                 job_name: str = None,
                 user: str = None,
                 nodes: str = None,
                 nodes_to_be_excluded: str = None,
                 ntasks: int = None,
                 cpus_per_task: int = None,
                 mem: str = None,
                 time: str = None,
                 output: str = None,
                 dry_run: bool = True,
                 path_to_registry: str = None,
                 wait: bool = False) -> None:
        """
        method to initialize the SbatchJobExecutionManager
        Args:
            conda_env (str): string defining the name of the conda env to be activated
            job_name (str): string defining the name of the job to be executed in slurm
            user (str): string defining the name of the user
            nodes (str): nodes to be used to run the slurm jobs
            nodes_to_be_excluded (str): string defining the nodes to be excluded
            ntasks (int): numer defining the number of tasks
            cpus_per_task (int): numer defining the cpus per tasks
            mem (str): string defining the amount of memory allocated for the executed commands
            time (int): time limit
            output (str): string defining the where to store the slurm output
            dry_run (bool): if true only the sbatch scripts to be fed to sbatch command will be
                            plot
            path_to_registry (str): path to the place where the list of executed commands will be saved
            wait (bool): if true the command blocks the program execution till the slurm jobs has
                         finished
        """

        self.conda_env = conda_env
        self.job_name = job_name
        self.user = user
        self.nodes = nodes
        self.nodes_to_be_excluded = nodes_to_be_excluded
        self.ntasks = ntasks
        self.cpus_per_task = cpus_per_task
        self.mem = mem
        self.time = time
        self.output = output
        self.dry_run = dry_run
        self.wait = wait
        self.path_to_registry = path_to_registry if path_to_registry else SbatchJobExecutionManager.path_to_registry
        if Path(self.path_to_registry).exists():
            self.load_registry()

    def execute_commands(self, commands: Union[str, List[str]]) -> None:
        """
        function to execute the command/commands provided in slurm.
        Each command is scheduled in a slurm job
        Args:
            commands: command/commands to be scheduled

        Returns:

        """
        if isinstance(commands, str):
            self.command_registry.append(commands)
            bash_sbatch_scripts = [self._generate_sbatch_scripts(commands)]
        elif isinstance(commands, list):
            [self.command_registry.append(command) for command in commands]
            bash_sbatch_scripts = [self._generate_sbatch_scripts(command) for command in commands]
        else:
            raise NotImplementedError(f"executed_commands is not implemented for input type {type(commands)}")

        if self.dry_run:
            for bash_sbatch_script in bash_sbatch_scripts:
                log.info("****************************")
                log.info(bash_sbatch_script)
                log.info("****************************")
                log.info("\n")
                self.command_registry.pop()

        else:
            for bash_sbatch_script in bash_sbatch_scripts:
                with tempfile.NamedTemporaryFile(mode="w", suffix='.sh', prefix=tempfile.gettempdir()) as tf:
                    tf_script = tf.name
                    tf.write(bash_sbatch_script)
                    tf.seek(0)
                    if self.wait:
                        cmd_sbatch = f"sbatch -W --exclude={self.nodes_to_be_excluded} {tf_script}"
                    else:
                        cmd_sbatch = f"sbatch --exclude={self.nodes_to_be_excluded} {tf_script}"
                    try:
                        subprocess.run(cmd_sbatch.split(" "), check=True)
                    except subprocess.CalledProcessError as e:
                        logging.exception(e)
                        logging.error(f"the following sbatch command failed:\n{cmd_sbatch}")
                        raise
        return

    def _generate_sbatch_scripts(self, command: str) -> str:
        """
        function to generate the sbatch scripts per job to be executed
        Args:
            command: command to be executed

        Returns:

        """
        return generate_sbatch_scripts(self.conda_env,
                                       command,
                                       self.job_name,
                                       self.user,
                                       self.nodes,
                                       self.ntasks,
                                       self.cpus_per_task,
                                       self.mem,
                                       self.time,
                                       self.output)

    def get_executed_commands(self):
        """function to get the list of executed commands"""
        return self.command_registry

    def print_executed_commands(self):
        """function to plot the executed commands"""
        for command in self.command_registry:
            log.info(command)

    def re_execute_all(self):
        """function to reexecute all commands"""
        self.execute_commands(deepcopy(self.command_registry))

    def save_registry(self):
        """function to save executed commands in the current session"""
        with open(self.path_to_registry, "wb") as f:
            pickle.dump(self.command_registry, f)

    def load_registry(self):
        """function to load executed command previously saved in the given path_to_registry"""
        with open(self.path_to_registry, "rb") as f:
            self.command_registry = pickle.load(f)
