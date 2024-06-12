import random
from slither import Slither
from brownie import accounts, network, project
import os
import time

def random_address():
    return "0x" + ''.join(random.choices('0123456789abcdef', k=40))

def random_uint256(max_value=2**256 - 1):
    return random.randint(0, max_value)

def random_int(min_value=-2**255, max_value=2**255 - 1):
    return random.randint(min_value, max_value)

def random_bool():
    return random.choice([True, False])

def random_bytes(length=32):
    return "0x" + ''.join(random.choices('0123456789abcdef', k=length*2))

def random_string(max_length=100):
    length = random.randint(1, max_length)
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=length))

def get_random_value(param_type):
    if 'uint' in param_type:
        return random_uint256()
    elif 'int' in param_type:
        return random_int()
    elif 'address' in param_type:
        return random_address()
    elif 'bool' in param_type:
        return random_bool()
    elif 'bytes' in param_type:
        length = int(param_type.replace('bytes', '')) if 'bytes' in param_type else 32
        return random_bytes(length)
    elif 'string' in param_type:
        return random_string()
    else:
        return 0

def get_contracts_info(project_path):
    slither = Slither(project_path)
    contracts_info = {}

    for contract in slither.contracts:
        contract_name = contract.name
        constructors = [f for f in contract.functions if f.is_constructor]
        if constructors:
            constructor = constructors[0]
            params = [(var.name, str(var.type)) for var in constructor.parameters]
        else:
            params = []
        contracts_info[contract_name] = params

    return contracts_info

def deploy_contracts(proj, contracts_info, dev, iteration):
    deployed_contracts = {}
    
    for contract_name, params in contracts_info.items():
        if contract_name not in proj:
            print(f"Contract {contract_name} not found in project.")
            continue

        constructor_args = [get_random_value(param_type) for param_name, param_type in params]

        try:
            contract = getattr(proj, contract_name)
            deployed_contract = contract.deploy(*constructor_args, {'from': dev})
            deployed_contracts[contract_name] = deployed_contract.address
            print(f"[{iteration}] Deployed {contract_name} at {deployed_contract.address}")
        except Exception as e:
            print(f"[{iteration}] Error deploying {contract_name}: {e}")
    
    return deployed_contracts

def main():
    project_path = '.'  # Adjust this to your project's path
    contracts_info = get_contracts_info(project_path)

    if not network.is_connected():
        try:
            network.connect('development')
            time.sleep(1)  # Add a short delay to ensure the network is fully connected
        except Exception as e:
            print(f"Failed to connect to network: {e}")
            return

    dev = accounts[0]

    try:
        if not project.get_loaded_projects():
            proj = project.load(os.path.basename(os.getcwd()))
        else:
            proj = project.get_loaded_projects()[0]
    except Exception as e:
        print(f"Failed to load project: {e}")
        return

    iterations = 1  # Number of fuzzing iterations

    for i in range(iterations):
        deploy_contracts(proj, contracts_info, dev, i)

    try:
        network.disconnect()
    except Exception as e:
        print(f"Failed to disconnect network: {e}")

if __name__ == "__main__":
    main()
