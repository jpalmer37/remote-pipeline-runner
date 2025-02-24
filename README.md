# Remote Pipeline Runner

A Python tool for running Nextflow pipelines on remote clusters. This tool handles:
1. Transferring input files to the remote cluster
2. Executing the pipeline command
3. Transferring results back to the local machine

## Requirements

- Python 3.6+
- Required Python packages (install using `pip install -r requirements.txt`):
  - paramiko
  - argparse

## Configuration

Create a `config.json` file with your pipeline configurations. Example:

```json
{
  "remote_config": {
    "host": "cluster.example.com",
    "user": "username"
  },
  "16s-analysis": {
    "remote_paths": {
      "database": "/path/to/remote/database",
      "input_dir": "/path/to/transferred/inputs",
      "output_dir": "/path/to/outputs",
      "work_dir": "/path/to/work"
    },
    "pipeline_command": "nextflow run 16s-pipeline.nf --input {input_dir} --output {output_dir} --database {database}"
  }
}
```

The configuration file has two main sections:
1. `remote_config`: Global settings for remote connection
   - `host`: The remote cluster hostname
   - `user`: SSH username for connection
2. Pipeline-specific configurations (e.g., "16s-analysis")
   - `remote_paths`: Directory paths on the remote system
   - `pipeline_command`: The command template to run the pipeline

## Usage

Basic command structure:
```powershell
python run_pipeline.py --name PIPELINE_NAME --input INPUT_DIR --output OUTPUT_DIR [--config CONFIG_FILE]
```

Example:
```powershell
python run_pipeline.py --name 16s-analysis --input C:\my\local\input --output C:\my\local\output
```

### Arguments

- `--name`: Name of the pipeline to run (must match a configuration in config.json)
- `--input`: Local directory containing input files
- `--output`: Local directory where results will be saved
- `--config`: (Optional) Path to config file (defaults to config.json in current directory)

## Authentication

The tool uses SSH for remote connection. Make sure to:
1. Have SSH access to the remote cluster
2. Set up SSH key-based authentication or be prepared to enter your password
3. Have the necessary permissions on the remote cluster

## Error Handling

The tool will:
- Validate the existence of input files and configurations
- Create necessary remote directories
- Provide feedback during file transfers and command execution
- Exit with status code 1 if any step fails