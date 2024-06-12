from slither import Slither
from brownie import accounts, network, project
import os

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

def main():
    project_path = '.'  # Adjust this to your project's path
    contracts_info = get_contracts_info(project_path)

    if not network.is_connected():
        try:
            network.connect('development')
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

    deployed_contracts = {}

    for contract_name, params in contracts_info.items():
        if contract_name not in proj:
            print(f"Contract {contract_name} not found in project.")
            continue

        constructor_args = []
        for param_name, param_type in params:
            if 'uint' in param_type:
                constructor_args.append(1e18)  # default value for uint types
            elif 'address' in param_type:
                constructor_args.append(dev.address)  # default address value
            elif 'string' in param_type:
                constructor_args.append("default")  # default string value
            elif 'bytes' in param_type:
                constructor_args.append(b"")  # default bytes value
            else:
                constructor_args.append(0)  # default value for other types

        try:
            contract = getattr(proj, contract_name)
            deployed_contract = contract.deploy(*constructor_args, {'from': dev})
            deployed_contracts[contract_name] = deployed_contract.address
            print(f"Deployed {contract_name} at {deployed_contract.address}")
        except Exception as e:
            print(f"Error deploying {contract_name}: {e}")

    for contract_name, address in deployed_contracts.items():
        print(f"Deployed {contract_name} at {address}")

    try:
        network.disconnect()
    except Exception as e:
        print(f"Failed to disconnect network: {e}")

if __name__ == "__main__":
    main()
