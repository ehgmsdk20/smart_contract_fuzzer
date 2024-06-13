import random
from slither import Slither
from slither.slither import SlitherError
from brownie import accounts, network, project
import os
import time
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.ticker import ScalarFormatter
from brownie.network.state import TxHistory
import subprocess
import re
import json

output_base_folder = "./output"


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
    plt.figure(figsize=(30, 7))

    # Define number of subplots based on unique functions
    num_functions = len(function_gas_usage)
    for i, (func, gas_usage) in enumerate(function_gas_usage.items(), 1):
        ax = plt.subplot(1, num_functions, i)
        plt.hist(gas_usage, bins=20, alpha=0.75, label=f'{func} Gas Usage')
        plt.axvline(expected_gas_usage[func][0], color='red', linestyle='dashed', linewidth=2, label='Expected Gas Usage Start')
        plt.axvline(expected_gas_usage[func][1], color='blue', linestyle='dashed', linewidth=2, label='Expected Gas Usage End')
        plt.title(f'{func.capitalize()}')
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
    ) if num_exceeded_txs > 0 else 1

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
    return percentage_exceeded, average_exceeded_ratio


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

def plot_results(contract_eval, output_folder):
    x = []
    y = []
    labels = []

    for contract_name, values in contract_eval.items():
        percentage_exceeded, average_exceeded_ratio = values[0], values[1]
        x.append(percentage_exceeded)
        y.append(average_exceeded_ratio)
        if percentage_exceeded != 0:
            labels.append(contract_name)
        else:
            labels.append("")
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y)

    for i, label in enumerate(labels):
        plt.annotate(label, (x[i], y[i]))

    plt.xlabel('Percentage Exceeded')
    plt.ylabel('Average Exceeded Ratio')
    plt.title('Contract Evaluation')

    plot_path = os.path.join(output_folder, 'contract_evaluation_plot.png')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    plt.savefig(plot_path)
    print(f"Plot saved to {plot_path}")
    plt.close()

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
    contract_eval = {}
    for contract_name, contract in deployed_contracts.items():
        contract_output_folder = os.path.join(output_base_folder, contract_name)
        if not os.path.exists(contract_output_folder):
            os.makedirs(contract_output_folder)
        error_output_file = os.path.join(contract_output_folder, "error_output.txt")
        gas_usage_file = os.path.join(contract_output_folder, "gas_usage.txt")
        try:
            error_logs, gas_usages = fuzz_contract(contract, contracts_info[contract_name])
            if gas_usage_file:
                percentage_exceeded, average_exceeded_ratio = plot(gas_usages, contract_output_folder, contract_name)
                contract_eval[contract_name] = [percentage_exceeded, average_exceeded_ratio]
                with open(error_output_file, 'w') as f:
                    for log in error_logs:
                        f.write(json.dumps(log) + "\n")
                    print(f"Error logs saved to {error_output_file}")

                with open(gas_usage_file, 'w') as f:
                    for usage in gas_usages:
                        f.write(json.dumps(usage) + "\n")
                    print(f"Gas usage logs saved to {gas_usage_file}")
                    
        except:
            pass
    reports_folder = os.path.join('.', 'reports')
    plot_results(contract_eval, reports_folder)
        
    try:
        network.disconnect()
    except Exception as e:
        print(f"Failed to disconnect network: {e}")


if __name__ == "__main__":
    main()
