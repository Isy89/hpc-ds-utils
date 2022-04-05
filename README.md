# hpc-ds-utils
Package providing tools to make life easier for people working in a HPC
cluster running slurm.
At the moment it provides:

- ***jlab_connector*** -> start jupyter lab server on remote and forward it to local computer
- ***SbatchJobExecutionManager*** class to generate sbatch scripts and execute them. It allows
  to store executed comands and load them back and reexecute them all.
  
```python
from hpc_ds_utils import SbatchJobExecutionManager

sbatch_manager = SbatchJobExecutionManager(output="test_dir", job_name="job_name", dry_run=True)
sbatch_manager.execute_commands("ls")
sbatch_manager.execute_commands(["run_pipeline1 args1 ... argsn",
                                 "run_pipeline2 args1 ... argsn"])
sbatch_manager.save_registry()
sbatch_manager.load_registry()
sbatch_manager.re_execute_all()
sbatch_manager.get_executed_commands()
sbatch_manager.print_executed_commands()

```

```
       _ _       _                                       _             
      (_) | __ _| |__     ___ ___  _ __  _ __   ___  ___| |_ ___  _ __ 
      | | |/ _` | '_ \   / __/ _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__|
      | | | (_| | |_) | | (_| (_) | | | | | | |  __/ (__| || (_) | |   
     _/ |_|\__,_|_.__/___\___\___/|_| |_|_| |_|\___|\___|\__\___/|_|   
    |__/            |_____|                                                                                       

    Easy way of setting up a permanent jupyter server on a remote server
    and forwarding it to your local computer.
    It requires conda and tmux to be installed in the remote server and
    conda to be initialized or the conda initializing code to be
    present in the .bashrc or in a .bash_conda file in the home directory
    in the remote server.
    A tmux session running a jupyter lab server at the required port is started, 
    the port forward to the local computer and jupyter lab opened in the
    browser
```

## installation
To install the package:

```bash
git clone https://github.com/Isy89/hpc-ds-utils.git && cd hpc-ds-utils/src
python -m setup bdist_wheel
python -m pip install dist/hpc_ds_utils-0.1-py3-none-any.whl
```

after installing the package the command ***jpc*** will be available on the command line.

supported OS: mac, linux ( windows maybe in the feature )

## Usage
***main script usage***

```bash
usage: jpc [-h] {kill_remote_tmux_session,check_tmux_session_up,check_remote_port_in_use,check_local_port_in_use,check_server_up,jp_start} ...
```  

The package provides the command jpc which is an interface to different sub commands. The principle one is the jpc jp_start

***jp_start*** -> main function starting the server, forwarding the port and opening jupyter lab in the web-browser

```bash
usage: jpc jp_start [-h] [--target TARGET] [--conda_env CONDA_ENV] [--tmux_session_name TMUX_SESSION_NAME] [--p_local P_LOCAL] [--p_remote P_REMOTE]

optional arguments:
  -h, --help            show this help message and exit
  --target TARGET       server address
  --conda_env CONDA_ENV
                        name of the conda env existing on the remote server to be activated
  --tmux_session_name TMUX_SESSION_NAME
                        name of the tmux session to be attached
  --p_local P_LOCAL     number of the port where to forward the remote jupyter session to
  --p_remote P_REMOTE   port of the remote server where the jupyter server is running
```

which starts the jupyter lab server in the remote machine and forwards it to the local web-browser
The jpc script apart from the jp_start contains the following set of subcommands for general task that
may be usefull to start and forward the rmeote jupyter lab server:

- ***check_tmux_session_up*** -> checks that a specific tmux session is already running 
```bash

usage: jpc check_tmux_session_up [-h] [--target TARGET] [--tmux_session_name TMUX_SESSION_NAME]

optional arguments:
  -h, --help            show this help message and exit
  --target TARGET       server address
  --tmux_session_name TMUX_SESSION_NAME
                        name of the tmux session to be attached
```
- ***kill_remote_tmux_session*** -> kills the provided tmux session in the remote server
```bash
usage: jpc kill_remote_tmux_session [-h] [--target TARGET] [--tmux_session_name TMUX_SESSION_NAME]

optional arguments:
  -h, --help            show this help message and exit
  --target TARGET       server address
  --tmux_session_name TMUX_SESSION_NAME
                        name of the tmux session to be attached
```
- ***check_remote_port_in_use*** -> check whether the provided port is already in used in the remote server
```bash

usage: jpc check_remote_port_in_use [-h] [--target TARGET] [--p_remote P_REMOTE]

optional arguments:
  -h, --help           show this help message and exit
  --target TARGET      server address
  --p_remote P_REMOTE  port of the remote server where the jupyter server is running

```
- ***check_local_port_in_use*** -> checks whether the provided port is already in used in the local machine
```bash

usage: jpc check_local_port_in_use [-h] [--p_local P_LOCAL]

optional arguments:
  -h, --help         show this help message and exit
  --p_local P_LOCAL  port of the remote server where the jupyter server is running
```
- ***check_server_up*** -> check wether a jupyter server is already running at the specific port
```bash

usage: jpc check_server_up [-h] [--target TARGET] [--p_remote P_REMOTE] [--conda_env CONDA_ENV]

optional arguments:
  -h, --help            show this help message and exit
  --target TARGET       server address
  --p_remote P_REMOTE   port of the remote server where the jupyter server is running
  --conda_env CONDA_ENV
                        name of the conda env existing on the remote server to be activated
```

