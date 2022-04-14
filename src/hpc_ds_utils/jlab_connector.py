import argparse
import logging
import shlex
import subprocess
import time
import webbrowser
from typing import Tuple

from rich import print

DESCRIPTION = (
    """
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
    """)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def ssh_minus_tt(x: str, target: str):
    """
    function to generate a bash command to execute a code on a remote server
    Args:
        x: the command to be executed
        target: the server address

    Returns:
        the command to be executed
    """
    return f'ssh -tt {target} "{x}"'


def run_command(cmd):
    return subprocess.run(shlex.split(cmd), check=True, capture_output=True)


def start_jupyter_server_remote(target: str, tmux_session_name: str, conda_env: str, port: int) -> None:
    """
    function to start a jupyter lab server on a remote server in a tmux session in a conda environment
    It requires the conda env to be present in the remote system and tmux to be installed
    Args:
        target: the server address
        tmux_session_name: name of the tmux session to start
        conda_env: name of the conda env to be activated. It requires jupyter to be present in the conda env
        port:port where to start the jupyter server

    Returns:

    """
    log.info(
        print(f"Starting a jupyter lab session in a tmux session called {tmux_session_name}"
              f" in {target} at {port} in conda env {conda_env}")
    )
    create_tmux_session = ssh_minus_tt(f"tmux new-session -d -s {tmux_session_name}", target)
    send_ctrl_c = ssh_minus_tt(f"tmux send-keys -t 0 C-c", target)
    rename_main_window = ssh_minus_tt(f"tmux rename-window -t 0 Main", target)
    split_view = ssh_minus_tt("tmux split-window -t 'Main' -v", target)
    activate_conda_env = ssh_minus_tt(f"tmux send-keys -t Main.0 'conda activate {conda_env}' Enter", target)
    start_jupyter_server_cmd = ssh_minus_tt(f"tmux send-keys -t Main.0 'jupyter lab --no-browser --port={port}' Enter",
                                            target)
    try:
        for cmd in [create_tmux_session, send_ctrl_c, rename_main_window, split_view, activate_conda_env,
                    start_jupyter_server_cmd]:
            log.info(f"running following command:\n{cmd}")
            run_command(cmd)
    except subprocess.CalledProcessError:
        log.error("something went wrong")
        raise
    return


def get_stdout_by_line_from_cmd_results(res_cmd) -> str:
    """function to extract the results of a command run in subprocess and return the stdout split on new lines"""
    return res_cmd.stdout.decode().split("\n")


def check_conda_env_exists(target: str, conda_env: str) -> Tuple[bool, str]:
    """
    function to check whether a conda environment exists in a remote server
    Args:
        target: remote server address
        conda_env: name of the conda env

    Returns:
        whether the conda env is present or not and the a string representing all the available conda envs
    """
    list_conda_envs = ssh_minus_tt(
        "conda env list",
        target
    )
    res_cmd = run_command(list_conda_envs)
    res_cmd_splitted_by_line = get_stdout_by_line_from_cmd_results(res_cmd)
    status = (
        True if len([i for i in res_cmd_splitted_by_line if conda_env in i]) > 0
        else False
    )
    available_envs = "\n".join(res_cmd_splitted_by_line)
    return status, available_envs


def check_running_server(target: str, conda_env: str, remote_port: int) -> bool:
    """
    function to check whether a jupyter server is already running in a remote server
    Args:
        target: remote server address
        conda_env: name of the conda env
        remote_port: port where to start the jupyter notebook on the remote server

    Returns:
        boolean defining whether or not a jupyter server is running on the remote server at the provided port
    """
    check_running_server_cmd = ssh_minus_tt(f"source .bash_conda; conda activate {conda_env}; jupyter server list",
                                            target)
    print(check_running_server_cmd)
    res_cmd = run_command(check_running_server_cmd)
    log.info(get_stdout_by_line_from_cmd_results(res_cmd))
    status = (
        True if len([i for i in get_stdout_by_line_from_cmd_results(res_cmd) if str(remote_port) in i]) > 0
        else False
    )
    log.info("The jp server is up" if status else "The jp server is not running")

    return status


def check_exists_bash_conda_file(target: str) -> bool:
    """
    function to check the presence on the remote system in the home directory whether the .bash_conda file is present.
    bash_conda file contains the conda initialization, which is generally present in the bashrc file. If the bash_conda
    file is not present, but the conda initialization code s present in the bashrc, the bash_coda file is generated and 
    the conda initialization code present in the bashrc is copied to it.
    This is done to allow sourcing of the file containing the conda initializing code. Bashrc cannot be sourced in non
    interactive mode.

    Args:
        target: remote server address

    Returns:

    """
    check_file_exists = ssh_minus_tt('[ -f .bash_conda ] && echo "File exist" || echo "File does not exist"', target)
    res_cmd = run_command(check_file_exists)
    log.info(print(get_stdout_by_line_from_cmd_results(res_cmd)))
    status = (True if len([i for i in get_stdout_by_line_from_cmd_results(res_cmd) if "File exist" in i]) > 0
              else False)
    log.info(f"{('.bash_conda exists' if status else '.bash_conda do not exists')}")
    return status


def check_conda_init_in_bashrc(target: str) -> bool:
    """
    check whether conda initializing code is present in the bashrc.
    Args:
        target: remote address

    Returns:

    """
    log.info(f"looking in bashrc for conda initialize and creating .bash_conda with conda initialize in it to"
             f"be able to source conda")
    check_conda_init_in_bashrc_cmd = ssh_minus_tt(
        'sed -n "/>>> conda initialize >>>/, /<<< conda initialize <<</p" .bashrc',
        target
    )
    res_cmd = run_command(check_conda_init_in_bashrc_cmd)
    status = True if "conda initialize" in get_stdout_by_line_from_cmd_results(res_cmd)[0] else False
    return status


def create_bash_conda_file(target: str):
    """
    create the bash_conda file on the remote server in the home directory
    Args:
        target: remote server address

    Returns:

    """
    create_bash_conda = ssh_minus_tt('touch .bash_conda', target)
    run_command(create_bash_conda)
    return


def copy_conda_initialize_in_bash_conda_file(target: str):
    """
    function to copy the conda initializing code from the bashrc to the bash_conda file
    Args:
        target: remote server address

    Returns:

    """
    create_bash_conda_with_conda_init_in_it = ssh_minus_tt(
        'sed -n \'/>>> conda initialize >>>/, /<<< conda initialize <<</p\' .bashrc > .bash_conda',
        target
    )
    run_command(create_bash_conda_with_conda_init_in_it)
    return


def check_tmux_session_running(target: str, tmux_session_name) -> bool:
    try:
        check_tmux_session_running_cmd = ssh_minus_tt(
            'tmux ls',
            target
        )
        res_cmd = run_command(check_tmux_session_running_cmd)
    except subprocess.CalledProcessError:
        pass
    status = (True if len([i for i in get_stdout_by_line_from_cmd_results(res_cmd) if tmux_session_name in i]) > 0
              else False)
    log.info("session is running" if status else "no session with this name is running")
    return status


def kill_tmux_session(target: str, tmux_session_name) -> None:
    kill_tmux_session_cmd = ssh_minus_tt(
        f'tmux kill-session -t {tmux_session_name}',
        target
    )
    try:
        run_command(kill_tmux_session_cmd)
    except subprocess.CalledProcessError:
        log.info("no running session")
        return


def check_if_jp_server_is_running(target: str, p_remote: int, conda_env: str) -> bool:
    """
    function to check that a jupyter server is running on a remote server. Bash_conda file is created if is not in the
    remote dir and filled with the conda initializing code present in the bashrc.

    Args:
        target: remote server address
        p_remote: port where to check for running server
        conda_env: name of the conda env

    Returns:

    """
    if not check_exists_bash_conda_file(target):

        if not check_conda_init_in_bashrc(target):
            raise RuntimeError("conda init is not present either in the bashrc and bash_conda do not exists."
                               " Aborting")
        else:

            create_bash_conda_file(target)
            copy_conda_initialize_in_bash_conda_file(target)

    try:
        return check_running_server(target, conda_env, p_remote)

    except subprocess.CalledProcessError:

        status, available_envs = check_conda_env_exists(target, conda_env)
        raise (
            ValueError(f"conda env: {conda_env} DO NOT EXISTS. possible env are: \n{available_envs}")
            if not status
            else RuntimeError("Something went wrong. Aborting.")
        )


def check_port_in_use_remote(target: str, p_remote: int) -> bool:
    """
    function to check if the selected port is already used in the remote server
    Args:
        target: remote server address
        p_remote: port number

    Returns:
        True if the port is in used False otherwise
    """
    status = False
    try:
        res_cmd = run_command(ssh_minus_tt(f"lsof -i :{p_remote}", target))
        if len(get_stdout_by_line_from_cmd_results(res_cmd)) > 0:
            status = True
    except subprocess.CalledProcessError:
        pass
    log.info(f"port {p_remote} is already in used" if status else f"port {p_remote} is not in used")
    return status


def check_port_in_use_local(p_local: int) -> bool:
    """
    function to check if the provided port is already used in the local machine
    Args:
        p_local: port number

    Returns:
        True if the port is in used False otherwise

    """
    status = False
    try:
        res_cmd = run_command(f"lsof -i:{p_local}")
        if len(get_stdout_by_line_from_cmd_results(res_cmd)) > 0:
            status = True
    except subprocess.CalledProcessError:
        pass
    log.info(f"port {p_local} is already in used" if status else f"port {p_local} is not in used")
    return status


def tunnel_jupyter_ports(target: str, p_local: int, p_remote: int, conda_env: str):
    """
    function to tunnel a remote jupyter running session from the remote to the local machine
    Args:
        target: remote server address
        p_local: local port where the jupyter session should be forwarded
        p_remote: remote port where the jupyter notebook is running
        conda_env: name of the conda env

    Returns:

    """
    log.info("waiting for the jupyter server to start")
    status = "down"
    while True:
        log.info(f"status is {status}")
        if status == "down":
            log.info(f"waiting")
            time.sleep(15)
            status = "up" if check_if_jp_server_is_running(target, p_remote, conda_env) else "down"
        else:
            break

    log.info(
        print(f"forwarding jupyter lab session running in {target} "
              f"at port {p_remote} to localhost at port {p_local}")
    )
    cmd = f'ssh -N -f -L localhost:{p_local}:localhost:{p_remote} {target}'
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        log.error("something went wrong")
        raise
    return


def jp_start_func(target: str, p_local: int, p_remote: int, tmux_session_name: str, conda_env: str) -> None:
    """
    function to start a jupyter lab server in a tmux session in a remote server and forward the port to the local
    machine and open the jupyter lab session in the web-browser
    Args:
        target: remote server address
        p_local: port where the jupyter lab session will be  forwarded
        p_remote: port number where the jupyter lab server is running on the remote server
        tmux_session_name: name of the tmux session to use
        conda_env: name of the conda environment to be activated

    Returns:

    """
    if check_port_in_use_local(p_local):
        log.error(f"port {p_local} already in use")
        raise ValueError
    if not check_if_jp_server_is_running(target, p_remote, conda_env):
        if check_tmux_session_running(target, tmux_session_name):
            kill_tmux_session(target, tmux_session_name)
        if check_port_in_use_remote(target, p_remote):
            log.error(f"port {p_remote} already in use in the remote server by another programm"
                      f"use a different remote port")
            raise ValueError
        start_jupyter_server_remote(target, tmux_session_name, conda_env,
                                    p_remote)

    tunnel_jupyter_ports(target, p_local, p_remote, conda_env)
    log.info(f'opening localhost:{p_local}')
    webbrowser.open_new_tab(f'http://localhost:{p_local}')
    return

def get_parser():
    main_parser = argparse.ArgumentParser(description=DESCRIPTION,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    sub_parser = main_parser.add_subparsers()

    kill_remote_tmux_session_parser = sub_parser.add_parser("kill_remote_tmux_session", help="")
    kill_remote_tmux_session_parser.add_argument("--target", type=str, help="server address")
    kill_remote_tmux_session_parser.add_argument("--tmux_session_name", type=str,
                                                 help="name of the tmux session to be attached")
    kill_remote_tmux_session_parser.set_defaults(
        func=kill_tmux_session
    )

    check_remote_tmux_session_running = sub_parser.add_parser("check_tmux_session_up", help="")
    check_remote_tmux_session_running.add_argument("--target", type=str, help="server address")
    check_remote_tmux_session_running.add_argument("--tmux_session_name", type=str,
                                                   help="name of the tmux session to be attached")
    check_remote_tmux_session_running.set_defaults(
        func=check_tmux_session_running
    )

    check_remote_port_in_use = sub_parser.add_parser("check_remote_port_in_use", help="")
    check_remote_port_in_use.add_argument("--target", type=str, help="server address")
    check_remote_port_in_use.add_argument("--p_remote", type=int,
                                          help="port of the remote server where the jupyter server is running")
    check_remote_port_in_use.set_defaults(
        func=check_port_in_use_remote
    )

    check_local_port_in_use = sub_parser.add_parser("check_local_port_in_use", help="")
    check_local_port_in_use.add_argument("--p_local", type=int,
                                         help="port of the remote server where the jupyter server is running")
    check_local_port_in_use.set_defaults(
        func=check_port_in_use_local
    )

    check_server_up = sub_parser.add_parser("check_server_up", help="")
    check_server_up.add_argument("--target", type=str, help="server address")
    check_server_up.add_argument("--p_remote", type=int,
                                 help="port of the remote server where the jupyter server is running")
    check_server_up.add_argument("--conda_env", type=str, help="name of the conda env existing "
                                                               "on the remote server to be activated")
    check_server_up.set_defaults(
        func=check_if_jp_server_is_running
    )

    jp_start = sub_parser.add_parser("jp_start",
                                     help="")
    jp_start.add_argument("--target", type=str, help="server address")
    jp_start.add_argument("--conda_env", type=str, help="name of the conda env existing "
                                                        "on the remote server to be activated")
    jp_start.add_argument("--tmux_session_name", type=str, help="name of the tmux session to be attached")
    jp_start.add_argument("--p_local", type=int,
                          help="number of the port where to forward the remote jupyter session to")
    jp_start.add_argument("--p_remote", type=int,
                          help="port of the remote server where the jupyter server is running")
    jp_start.set_defaults(
        func=jp_start_func
    )
    return main_parser


def main_func():
    """main function of the script and one of the entry points of the package.It parses the arguments provided and run
    the specified command."""

    main_parser = get_parser()
    args = main_parser.parse_args()
    variables = vars(args)

    args.func(**{key: variables[key] for key in variables if key != "func"})
    return


if __name__ == "__main__":
    main_func()
