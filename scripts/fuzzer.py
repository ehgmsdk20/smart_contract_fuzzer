import json
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

# 퍼징 함수
def fuzz_contract(contract, functions):
    test_cases = generate_test_cases(functions)
    for case in test_cases:
        try:
            eval(f'contract.{case}({{"from": accounts[1]}})')
        except Exception as e:
            print(f"Error encountered during fuzzing with {case}: {e}")

# 테스트 케이스 생성 함수
def generate_test_cases(functions):
    test_cases = []
    for func in functions:
        if func['name'] != 'constructor':
            for param in func['parameters']:
                param_type, param_name = param
                if param_type == 'address':
                    test_cases.append(f"{func['name']}('0x0000000000000000000000000000000000000000')")
                elif param_type == 'uint256':
                    test_cases.append(f"{func['name']}(10**18)")
                    test_cases.append(f"{func['name']}(-1)")
    return test_cases

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
