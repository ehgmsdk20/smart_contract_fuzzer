import random
from slither import Slither
from slither.slither import SlitherError
from brownie import accounts, network, project
import os
import time
from brownie.network.state import TxHistory
import subprocess
import re


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

def generate_test_cases(functions, num_cases=5):
    test_cases = []
    for func in functions:
        if func['name'] != 'constructor':
            for _ in range(num_cases):
                params = []
                for param in func['parameters']:
                    param_type, param_name = param
                    if param_type == 'address':
                        params.append(random_address())
                    elif param_type.startswith('uint'):
                        params.append(random_uint256(100000))
                    elif param_type.startswith('int'):
                        params.append(random_int())
                    elif param_type == 'bool':
                        params.append(random_bool())
                    elif param_type.startswith('bytes'):
                        length = int(param_type[5:]) if param_type != 'bytes' else 32
                        params.append(random_bytes(length))
                    elif param_type == 'string':
                        params.append(random_string()) 
                test_cases.append((func['name'], params, func['payable']))
    return test_cases


def set_solc_version(contract_path):
    with open(contract_path, 'r') as file:
        content = file.read()
    pragma_match = re.search(r'pragma\s+solidity\s+([^;]+);', content)
    if pragma_match:
        version = pragma_match.group(1).strip()
        version = re.split(r'[<>=^]', version)[-1].strip()  # Extract exact version if specified
        print(f"Setting solc version to {version}")
        subprocess.run(['solc-select', 'install', version])
        subprocess.run(['solc-select', 'use', version])
    else:
        raise Exception("No pragma solidity version found in contract.")


def save_gas_usage(contract_name, constructor_args, gas_used, iteration):
    output_dir = f"output/{contract_name}"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "gas_usage.txt")
    
    with open(file_path, "a") as file:
        file.write(f"Iteration {iteration}\n")
        file.write(f"Input values: {constructor_args}\n")
        file.write(f"Gas used: {gas_used}\n\n")

def get_contracts_info(contract_path):
    try:
        #set_solc_version(contract_path)
        slither = Slither(contract_path)
        contracts = slither.contracts
        if not contracts:
            print(f"No contracts found in {contract_path}")
            return []
        functions_per_contracts = {}
        for contract in contracts:
            functions = []
            for func in contract.functions:
                func_name = func.name
                param_list = []
                for param in func.parameters:
                    try:
                        param_type = param.type.type 
                        param_list.append((param_type, param.name))
                    except AttributeError:
                        continue
                if not func.view:
                    functions.append({
                        'name': func_name, 
                        'parameters': param_list, 
                        'payable': func.payable
                    })
            functions_per_contracts[contract.name] = functions
        return functions_per_contracts
    except SlitherError as e:
        print(f"Error while parsing the contract: {e}")
        return {}

def deploy_contracts(proj, contracts_info, dev):
    deployed_contracts = {}
    
    for contract_name, functions in contracts_info.items():
        if contract_name not in proj:
            print(f"Contract {contract_name} not found in project.")
            continue

        try:
            contract = getattr(proj, contract_name)
            tx = contract.deploy({'from': dev})
            deployed_contracts[contract_name] = tx
            gas_used = tx.tx.gas_used
            print(f"Deployed {contract_name} at {tx.address} with gas used: {gas_used}")

            
        except Exception as e:
            print(f"Error deploying {contract_name}: {e}")
    
    return deployed_contracts

def fuzz_contract(contract, functions):
    error_logs = []
    gas_usages = []
    test_cases = generate_test_cases(functions, num_cases=100)  
    random.shuffle(test_cases)
    history = TxHistory()

    for case in test_cases:
        value = random_int(0, 10000)
        func_name, params, payable = case
        try:
            func = getattr(contract, func_name)
            msg = {'from': accounts[1]}
            if payable:
                msg['value'] = value
            if params:
                tx = func(*params, msg)
            else:
                tx = func(msg)
            

            gas_usages.append({
                "function": func_name,
                "params": params,
                "msg.sender": accounts[1].address,
                "msg.value": value,
                "gas_used": tx.gas_used,
                "transaction_hash": tx.txid
            })
        except Exception as e:
            tx = history[-1] if len(history) > 0 else None
            gas_usages.append({
                "function": func_name,
                "params": params,
                "msg.sender": accounts[1].address,
                "msg.value": value,
                "gas_used": tx.gas_used if tx else "N/A",
                "transaction_hash": tx.txid if tx else "N/A"
            })
            error_log = {
                "function": func_name,
                "params": params,
                "error": str(e),
                "raw_error": tx.input if tx else "N/A",
                "gas_used": tx.gas_used if tx else "N/A",
                "transaction_hash": tx.txid if tx else "N/A"
            }
            error_logs.append(error_log)
    return error_logs, gas_usages

def main():
    project_path = '.'  # Adjust this to your project's path
    #set_solc_version(project_path)
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


    deployed_contracts = deploy_contracts(proj, contracts_info, dev)
    for contract_name, contract in deployed_contracts.items():
        try:
            error_logs, gas_usages = fuzz_contract(contract, contracts_info[contract_name])
        except:
            pass
        #print(gas_usages)

    try:
        network.disconnect()
    except Exception as e:
        print(f"Failed to disconnect network: {e}")

if __name__ == "__main__":
    main()
