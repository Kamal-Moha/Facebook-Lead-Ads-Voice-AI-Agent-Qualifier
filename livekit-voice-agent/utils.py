import os
import boto3
import yaml


def load_prompt(filename):
    """Load a prompt from a YAML file."""
    script_dir = os.getcwd()
    prompt_path = os.path.join(script_dir, "prompts", filename)

    try:
        with open(prompt_path, "r") as file:
            prompt_data = yaml.safe_load(file)
            return prompt_data.get("instructions", "")
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Error loading prompt file {filename}: {e}")
        return ""

# define a function that uploads a file to an S3 bucket
def upload_cs_file(bucket_name, source_file_name, destination_file_name):
    s3 = boto3.client("s3")
    s3.upload_file(source_file_name, bucket_name, destination_file_name)
    return True


# define a function that generates the public URL
def get_cs_file_url(bucket_name, file_name):
    url = f"https://{bucket_name}.s3.eu-north-1.amazonaws.com/{file_name}"
    return url
