import json
import random
from slither import Slither
from brownie import accounts, project
from slither.slither import SlitherError

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
def random_uint256():
    return random.randint(0, 2**256 - 1)

# 테스트 케이스 생성 함수
def generate_test_cases(functions, num_cases=100):
    test_cases = []
    for func in functions:
        if func['name'] != 'constructor':
            for _ in range(num_cases):
                params = []
                for param in func['parameters']:
                    param_type, param_name = param
                    if param_type == 'address':
                        params.append(f"'{random_address()}'")
                    elif param_type == 'uint256':
                        params.append(f"{random_uint256()}")
                test_cases.append(f"{func['name']}({', '.join(params)})")
    return test_cases

# 퍼징 함수
def fuzz_contract(contract, functions):
    test_cases = generate_test_cases(functions)
    for case in test_cases:
        try:
            eval(f'contract.{case}({{"from": accounts[1]}})')
        except Exception as e:
            print(f"Error encountered during fuzzing with {case}: {e}")

# 메인 함수
def main():
    contract_path = "contracts/Vulnerable.sol"
    functions = extract_functions(contract_path)
    if not functions:
        print("No functions extracted. Exiting...")
        return
    print(f"Extracted functions: {json.dumps(functions, indent=2)}")
    contract = deploy_contract()
    fuzz_contract(contract, functions)

if __name__ == "__main__":
    main()
