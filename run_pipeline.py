#!/usr/bin/env python3

import argparse
import json
import os
import sys
import paramiko
from pathlib import Path

class RemotePipelineRunner:
    def __init__(self, config_file='config.json'):
        self.config = self._load_config(config_file)
        self.ssh = None
        self.sftp = None

    def _load_config(self, config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'remote_config' not in config:
                    print("Error: 'remote_config' section not found in config file")
                    sys.exit(1)
                return config
        except FileNotFoundError:
            print(f"Error: Config file {config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in config file {config_file}")
            sys.exit(1)

    def connect(self):
        try:
            remote_config = self.config['remote_config']
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                remote_config['host'],
                username=remote_config['user']
            )
            self.sftp = self.ssh.open_sftp()
        except KeyError as e:
            print(f"Error: Missing required field in remote_config: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error connecting to remote host: {e}")
            sys.exit(1)

    def _transfer_files(self, local_path, remote_path, direction='up'):
        try:
            local_path = Path(local_path)
            if not local_path.exists() and direction == 'up':
                print(f"Error: Local path {local_path} does not exist")
                return False

            if local_path.is_file():
                if direction == 'up':
                    remote_file = str(Path(remote_path) / local_path.name)
                    self._ensure_remote_dir(str(Path(remote_file).parent))
                    self.sftp.put(str(local_path), remote_file)
                else:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    self.sftp.get(remote_path, str(local_path))
            else:
                for item in local_path.glob('**/*'):
                    if item.is_file():
                        rel_path = item.relative_to(local_path)
                        if direction == 'up':
                            remote_file = str(Path(remote_path) / rel_path)
                            remote_dir = str(Path(remote_file).parent)
                            self._ensure_remote_dir(remote_dir)
                            self.sftp.put(str(item), remote_file)
                        else:
                            local_file = Path(local_path) / rel_path
                            local_file.parent.mkdir(parents=True, exist_ok=True)
                            self.sftp.get(str(Path(remote_path) / rel_path), str(local_file))
            return True
        except Exception as e:
            print(f"Error transferring files: {e}")
            return False

    def _ensure_remote_dir(self, remote_path):
        try:
            self.sftp.stat(remote_path)
        except FileNotFoundError:
            stdin, stdout, stderr = self.ssh.exec_command(f'mkdir -p {remote_path}')
            if stdout.channel.recv_exit_status() != 0:
                print(f"Error creating remote directory: {stderr.read().decode()}")
                return False
            return True

    def _execute_remote_command(self, command):
        try:
            print(f"Executing command: {command}")
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print("Remote command failed:")
                print(stderr.read().decode())
                return False
            
            print("Remote command output:")
            print(stdout.read().decode())
            return True
        except Exception as e:
            print(f"Error executing remote command: {e}")
            return False

    def run_pipeline(self, pipeline_name, input_path, output_path):
        if pipeline_name not in self.config:
            print(f"Error: Pipeline '{pipeline_name}' not found in config")
            return False

        pipeline_config = self.config[pipeline_name]
        if 'remote_paths' not in pipeline_config or 'pipeline_command' not in pipeline_config:
            print(f"Error: Invalid pipeline configuration for '{pipeline_name}'")
            return False

        remote_paths = pipeline_config['remote_paths']

        print("Connecting to remote host...")
        self.connect()

        print("Transferring input files to remote host...")
        if not self._transfer_files(input_path, remote_paths['input_dir']):
            return False

        print("Executing pipeline command...")
        command = pipeline_config['pipeline_command'].format(
            input_dir=remote_paths['input_dir'],
            output_dir=remote_paths['output_dir'],
            database=remote_paths['database']
        )
        if not self._execute_remote_command(command):
            return False

        print("Transferring results back to local machine...")
        if not self._transfer_files(output_path, remote_paths['output_dir'], direction='down'):
            return False

        print("Pipeline execution completed successfully!")
        return True

    def __del__(self):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()

def main():
    parser = argparse.ArgumentParser(description='Remote Pipeline Runner')
    parser.add_argument('--name', required=True, help='Name of the pipeline to run')
    parser.add_argument('--input', required=True, help='Local input directory')
    parser.add_argument('--output', required=True, help='Local output directory')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    runner = RemotePipelineRunner(args.config)
    success = runner.run_pipeline(args.name, args.input, args.output)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()