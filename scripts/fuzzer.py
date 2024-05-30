import json
from solidity_parser import parser
from brownie import accounts, project

# 스마트 컨트랙트 컴파일 및 배포
def deploy_contract():
    proj = project.load('.', name="VulnerableProject")
    proj.load_config()
    Vulnerable = proj.Vulnerable
    return Vulnerable.deploy({'from': accounts[0]})

# 함수 정보 추출 함수
def extract_functions(solidity_code):
    ast = parser.parse(solidity_code)
    functions = []
    for item in ast['children']:
        if item['type'] == 'ContractDefinition':
            for sub_item in item['subNodes']:
                if sub_item['type'] == 'FunctionDefinition':
                    func_name = sub_item['name']
                    parameters = sub_item['parameters']['parameters']
                    param_list = [(param['typeName']['name'], param['name']) for param in parameters]
                    functions.append({'name': func_name, 'parameters': param_list})
    return functions

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
    with open('contracts/Vulnerable.sol', 'r') as file:
        solidity_code = file.read()
    
    functions = extract_functions(solidity_code)
    contract = deploy_contract()
    fuzz_contract(contract, functions)

if __name__ == "__main__":
    main()
