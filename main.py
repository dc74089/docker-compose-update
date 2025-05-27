#!/usr/bin/env python3

import argparse
import yaml
from pathlib import Path
import docker
import git
import subprocess


def get_docker_client():
    try:
        return docker.from_env()
    except docker.errors.DockerException as e:
        print(f"Error connecting to Docker daemon: {e}")
        exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('compose_file', help='Path to docker-compose.yml file')
    args = parser.parse_args()

    compose_file = Path(args.compose_file)
    if not compose_file.exists():
        print(f"Error: {compose_file} does not exist")
        exit(1)

    client = get_docker_client()
    project_name = compose_file.stem

    # Update git repositories for local builds
    pulled_repos = []
    with open(compose_file) as f:
        compose_config = yaml.safe_load(f)
        services = compose_config.get('services', {})

        for service in services.values():
            if 'build' in service:
                build_context = service['build']
                if isinstance(build_context, dict):
                    build_context = build_context.get('context', '.')
                if build_context in pulled_repos:
                    continue
                if Path(build_context).exists():
                    try:
                        print(f"Updating git repository at {build_context}")
                        repo = git.Repo(build_context)
                        repo.remotes.origin.pull()
                        pulled_repos.append(build_context)
                    except git.exc.GitCommandError as e:
                        print(f"Error updating git repository at {build_context}: {e}")

    # Pull, build and deploy stack using docker-compose
    project_dir = str(compose_file.parent)
    config_path = str(compose_file)

    try:
        # Pull images
        subprocess.run(['docker-compose', '-f', config_path, '-p', project_name, 'pull'], check=True)
        # Build services
        subprocess.run(['docker-compose', '-f', config_path, '-p', project_name, 'build'], check=True)
        # Up services
        subprocess.run(['docker-compose', '-f', config_path, '-p', project_name, 'up', '-d'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building or deploying stack: {e}")
        exit(1)


if __name__ == '__main__':
    main()