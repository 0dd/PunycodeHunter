import argparse
import itertools
import idna
import boto3
import time
import random
import yaml
from botocore.exceptions import ClientError
from typing import Dict, List
from prettytable import PrettyTable


def load_yaml_config(path: str) -> Dict[str, List[str]]:
    with open(path, 'r') as file:
        return yaml.safe_load(file)


client = boto3.client('route53domains', region_name='us-east-1')

config_path = 'similar_chars.yaml'
similar_chars = load_yaml_config(config_path)['similar_chars']


def generate_domains(base_domain: str) -> List[str]:
    """Generate all possible similar looking domain names."""
    base_part = base_domain[:-4]  # 去除 '.com'
    combinations = itertools.product(*(similar_chars.get(char, [char]) for char in base_part))
    return [''.join(combination) + '.com' for combination in combinations]


def to_punycode(domain: str) -> str:
    """Convert a Unicode domain to Punycode if valid."""
    try:
        return idna.encode(domain).decode('ascii')
    except idna.IDNAError:
        # print(f"Error converting {domain} to Punycode.")
        return None


def check_domain_availability(domain: str, max_retries: int = 5) -> str:
    """Check if a domain is available for purchase using AWS Route 53 with retry logic."""
    for attempt in range(max_retries):
        try:
            response = client.check_domain_availability(DomainName=domain)
            # print(response)
            return response['Availability']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt == max_retries - 1:
                    return "Rate limit exceeded"
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limit hit. Waiting for {wait_time:.2f} seconds before retry.")
                time.sleep(wait_time)
            else:
                return str(e)
    return "Max retries reached"


def main(base_domain):
    domains = generate_domains(base_domain)

    table = PrettyTable()
    table.field_names = ["Original Domain", "Punycode", "Availability"]
    table.align["Original Domain"] = "l"
    table.align["Punycode"] = "l"
    table.align["Availability"] = "l"

    print("Checking domain availability...")
    print(table.field_names)
    print("-" * (sum(len(field) for field in table.field_names) + 6))

    for domain in domains:
        punycode = to_punycode(domain)
        if punycode is None:
            continue
        availability = check_domain_availability(punycode)
        table.add_row([domain, punycode, availability])
        print(table.rows[-1])
        time.sleep(1)

    print("\nFull Results:")
    print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check domain availability for similar-looking domains.")
    parser.add_argument("domain", help="The base domain to check for similar-looking domains.")
    args = parser.parse_args()
    main(args.domain)
