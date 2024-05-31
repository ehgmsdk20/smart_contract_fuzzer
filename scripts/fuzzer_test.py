import json
import random
from slither import Slither
from brownie import accounts, project, network
from slither.slither import SlitherError
from brownie.network.state import TxHistory
import os

gas_limit = 100000  # 수정된 가스 한도
output_folder = "./output"
error_output_file = os.path.join(output_folder, "error_output.txt")
gas_usage_file = os.path.join(output_folder, "gas_usage.txt")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

error_logs = []
gas_usages = []

# 스마트 컨트랙트 컴파일 및 배포
def deploy_contract():
    proj = project.load('.', name="VulnerableProject")
    proj.load_config()
    Vulnerable = proj.Vulnerable
    return Vulnerable.deploy({'from': accounts[0]})

# 함수 정보 추출 함수
def extract_functions(contract_path):
    try:
        slither = Slither(contract_path)
        contracts = slither.contracts
        if not contracts:
            print(f"No contracts found in {contract_path}")
            return []
        contract = contracts[0]  # Assuming there's only one contract
        functions = []
        for func in contract.functions:
            func_name = func.name
            param_list = [(param.type.type, param.name) for param in func.parameters]
            functions.append({'name': func_name, 'parameters': param_list})
        return functions
    except SlitherError as e:
        print(f"Error while parsing the contract: {e}")
        return []

# 무작위 주소 생성
def random_address():
    return "0x" + ''.join(random.choices('0123456789abcdef', k=40))

# 무작위 uint256 값 생성
def random_uint256(max_value=2**256 - 1):
    return random.randint(0, max_value)

# 무작위 int 값 생성
def random_int(min_value=-2**255, max_value=2**255 - 1):
    return random.randint(min_value, max_value)

# 무작위 bool 값 생성
def random_bool():
    return random.choice([True, False])

# 무작위 bytes 값 생성
def random_bytes(length=32):
    return "0x" + ''.join(random.choices('0123456789abcdef', k=length*2))

# 무작위 string 값 생성
def random_string(max_length=100):
    length = random.randint(1, max_length)
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=length))

# 테스트 케이스 생성 함수
def generate_test_cases(functions, num_cases=5):
    test_cases = []
    for func in functions:
        if func['name'] != 'constructor' and func['name'] != 'deposit':
            for _ in range(num_cases):
                params = []
                for param in func['parameters']:
                    param_type, param_name = param
                    if param_type == 'address':
                        params.append(random_address())
                    elif param_type.startswith('uint'):
                        params.append(random_uint256(10**18))  # 현실적인 값으로 범위 제한
                    elif param_type.startswith('int'):
                        params.append(random_int())
                    elif param_type == 'bool':
                        params.append(random_bool())
                    elif param_type.startswith('bytes'):
                        length = int(param_type[5:]) if param_type != 'bytes' else 32
                        params.append(random_bytes(length))
                    elif param_type == 'string':
                        params.append(random_string()) 
                test_cases.append((func['name'], params))
    return test_cases

# 퍼징 함수
def fuzz_contract(contract, functions):
    test_cases = generate_test_cases(functions, num_cases=20)  # 더 많은 테스트 케이스 생성
    history = TxHistory()

    # 초기 입금 설정
    deposit_amount = 3*10**18  # 3 Ether
    for i in range(1, 3):  # accounts[1]과 accounts[2]에 입금
        try:
            tx = contract.deposit({'from': accounts[i], 'value': deposit_amount})
            gas_usages.append({
                "function": "deposit",
                "params": [deposit_amount],
                "gas_used": tx.gas_used,
                "transaction_hash": tx.txid
            })
        except Exception as e:
            tx = history[-1] if len(history) > 0 else None
            gas_usages.append({
                "function": "deposit",
                "params": [deposit_amount],
                "gas_used": tx.gas_used,
                "transaction_hash": tx.txid
            })
            error_log = {
                "function": "deposit",
                "params": [deposit_amount],
                "error": str(e),
                "raw_error": tx.input if tx else "N/A",
                "gas_used": tx.gas_used if tx else "N/A",
                "transaction_hash": tx.txid if tx else "N/A"
            }
            error_logs.append(error_log)
            print(f"Failed to deposit for account {i}: {str(e)}")

    for case in test_cases:
        func_name, params = case
        try:
            func = getattr(contract, func_name)
            if params:
                tx = func(*params, {'from': accounts[1]})
            else:
                tx = func({'from': accounts[1]})
            gas_usages.append({
                "function": func_name,
                "params": params,
                "gas_used": tx.gas_used,
                "transaction_hash": tx.txid
            })
        except Exception as e:
            tx = history[-1] if len(history) > 0 else None
            gas_usages.append({
                "function": func_name,
                "params": params,
                "gas_used": tx.gas_used,
                "transaction_hash": tx.txid
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

def analyze_gas_usage(tx, case):
    if tx.gas_used > gas_limit:
        print(f"Warning: High gas usage({tx.gas_used}) for {case}")

# 프로퍼티 기반 테스트
def property_based_tests(contract):
    try:
        # Example property: balances for all accounts should never be negative
        for account in accounts[:3]:
            balance = contract.balances(account)
            assert balance >= 0, f"Account {account} has negative balance"
        print("Property test passed: All balances are non-negative.")
    except Exception as e:
        error_logs.append({
            "error": f"Property test failed: {e}"
        })

# 메인 함수
def main():
    if not network.is_connected():
        network.connect('development')  # 로컬 개발 네트워크에 연결
    contract_path = "contracts/Vulnerable.sol"
    functions = extract_functions(contract_path)
    if not functions:
        print("No functions extracted. Exiting...")
        return
    contract = deploy_contract()
    fuzz_contract(contract, functions)
    property_based_tests(contract)

    with open(error_output_file, 'w') as f:
        for log in error_logs:
            f.write(json.dumps(log) + "\n")
        print(f"Error logs saved to {error_output_file}")

    with open(gas_usage_file, 'w') as f:
        for usage in gas_usages:
            f.write(json.dumps(usage) + "\n")
        print(f"Gas usage logs saved to {gas_usage_file}")

if __name__ == "__main__":
    main()
