import json
import random
from slither import Slither
from brownie import accounts, project, network
from slither.slither import SlitherError
from brownie.network.state import TxHistory
import os
import glob
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.ticker import ScalarFormatter
import subprocess
import re

output_base_folder = "./output"

if not os.path.exists(output_base_folder):
    os.makedirs(output_base_folder)

def deploy_contract(contract_name):
    proj = project.load('.', name=contract_name)
    proj.load_config()
    Contract = getattr(proj, contract_name)
    return Contract.deploy({'from': accounts[0]})

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

def extract_functions(contract_path):
    try:
        set_solc_version(contract_path)
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
                param_list = [(param.type.type, param.name) for param in func.parameters]
                functions.append({
                    'name': func_name, 
                    'parameters': param_list, 
                    'payable': func.payable,
                    'view': func.view
                })
            functions_per_contracts[contract.name] = functions
        return functions_per_contracts
    except SlitherError as e:
        print(f"Error while parsing the contract: {e}")
        return {}

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
                test_cases.append((func['name'], params, func['payable'], func['view']))
    return test_cases

def plot(gas_usages, output_folder, contract_name):
    function_gas_usage = defaultdict(list)
    unexpected_conditions = []

    for tx in gas_usages:
        function_gas_usage[tx['function']].append(tx['gas_used'])

    # Calculate expected gas usage (most common bin range) for each function
    expected_gas_usage = {}
    for func, gas in function_gas_usage.items():
        counts, bin_edges = np.histogram(gas, bins=20)
        max_bin_index = np.argmax(counts)
        expected_gas_usage[func] = (bin_edges[max_bin_index], bin_edges[max_bin_index + 1])

    # Plot the data
    plt.figure(figsize=(14, 7))

    # Define number of subplots based on unique functions
    num_functions = len(function_gas_usage)
    for i, (func, gas_usage) in enumerate(function_gas_usage.items(), 1):
        ax = plt.subplot(1, num_functions, i)
        plt.hist(gas_usage, bins=20, alpha=0.75, label=f'{func} Gas Usage')
        plt.axvline(expected_gas_usage[func][0], color='red', linestyle='dashed', linewidth=2, label='Expected Gas Usage Start')
        plt.axvline(expected_gas_usage[func][1], color='blue', linestyle='dashed', linewidth=2, label='Expected Gas Usage End')
        plt.title(f'{func.capitalize()} Function Gas Usage')
        plt.xlabel('Gas Used')
        plt.ylabel('Frequency')

        # Highlight points above the expected threshold and collect unexpected conditions
        for tx in gas_usages:
            if tx['function'] == func and tx['gas_used'] > expected_gas_usage[func][1]:
                unexpected_conditions.append(tx)
        high_gas_usages = [tx['gas_used'] for tx in gas_usages if tx['function'] == func and tx['gas_used'] > expected_gas_usage[func][1]]
        ax.plot(high_gas_usages, [0.5] * len(high_gas_usages), 'ro', label='Above Expected')
        
        plt.legend()

        ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))


    plt.tight_layout()
    output_file = os.path.join(output_folder, f'gas_usage_{contract_name}.png')
    plt.savefig(output_file)
    plt.close()
    print(f"Gas usage plot saved to {output_file}")

    # Calculate additional statistics
    total_txs = len(gas_usages)
    num_exceeded_txs = len(unexpected_conditions)
    percentage_exceeded = (num_exceeded_txs / total_txs) * 100 if total_txs > 0 else 0
    average_exceeded_ratio = np.mean(
        [tx['gas_used'] / expected_gas_usage[tx['function']][1] for tx in unexpected_conditions]
    ) if num_exceeded_txs > 0 else 0

    # Save unexpected conditions to a file
    unexpected_file = os.path.join(output_folder, 'unexpected_condition.txt')
    with open(unexpected_file, 'w') as f:
        f.write(f"Percentage of transactions exceeding expected gas usage: {percentage_exceeded:.2f}%\n")
        f.write(f"Average exceeded gas usage ratio: {average_exceeded_ratio:.2f}\n\n")
        for condition in unexpected_conditions:
            f.write(f"Function: {condition['function']}\n")
            f.write(f"Gas Used: {condition['gas_used']}\n")
            f.write(f"Params: {condition.get('params', 'N/A')}\n")
            f.write(f"Msg.value: {condition.get('msg.value', 'N/A')}\n")
            f.write("\n")
    print(f"Unexpected conditions saved to {unexpected_file}")

def fuzz_contract(contract, functions):
    error_logs = []
    gas_usages = []
    test_cases = generate_test_cases(functions, num_cases=100)  
    random.shuffle(test_cases)
    history = TxHistory()

    for case in test_cases:
        value = random_int(0, 10000)
        func_name, params, payable, view = case
        try:
            func = getattr(contract, func_name)
            msg = {'from': accounts[1]}
            if payable:
                msg['value'] = value
            if params:
                tx = func(*params, msg)
            else:
                tx = func(msg)
            
            if not view:
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
    if not network.is_connected():
        network.connect('development') 

    contract_files = glob.glob("contracts/*.sol")
    if not contract_files:
        print("No contract files found. Exiting...")
        return
    for contract_file in contract_files:
        contract_name = os.path.splitext(os.path.basename(contract_file))[0]
        functions_per_contracts = extract_functions(contract_file)
        for contract_name, functions in functions_per_contracts.items():
            if not functions:
                print(f"No functions extracted for {contract_name}. Skipping...")
                continue
            print(f"Testing contract: {contract_name}")

            contract_output_folder = os.path.join(output_base_folder, contract_name)
            if not os.path.exists(contract_output_folder):
                os.makedirs(contract_output_folder)
            error_output_file = os.path.join(contract_output_folder, "error_output.txt")
            gas_usage_file = os.path.join(contract_output_folder, "gas_usage.txt")

            try:
                contract = deploy_contract(contract_name)
                error_logs, gas_usages = fuzz_contract(contract, functions)
                plot(gas_usages, contract_output_folder, contract_name)
                
                with open(error_output_file, 'w') as f:
                    for log in error_logs:
                        f.write(json.dumps(log) + "\n")
                    print(f"Error logs saved to {error_output_file}")

                with open(gas_usage_file, 'w') as f:
                    for usage in gas_usages:
                        f.write(json.dumps(usage) + "\n")
                    print(f"Gas usage logs saved to {gas_usage_file}")
            except Exception as e:
                print(f"Deploying contract {contract_name} failed")

if __name__ == "__main__":
    main()
