# Smart Contract Fuzzer

This project is a smart contract fuzzer designed to identify vulnerabilities and abnormal gas usage in Solidity smart contracts. The fuzzer performs the following tasks:

1. Parsing contracts with Slither
2. Test case generation
3. Measuring gas usage
4. Identifying abnormal gas usage

## Prerequisites

Make sure you have the following installed:

- Python 3.11.7
- Node.js
- `solc` (Solidity compiler)
- [Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html)

## Setup

1. Clone this repository:
    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Run the setup script to install the required dependencies:
    ```sh
    source setting.sh
    ```

This will perform the following actions:
- Install the Python dependencies listed in `requirements.txt`
- Install Ganache globally using npm
- Install and use Solidity compiler version 0.8.6

## Usage

To use the smart contract fuzzer:

1. Add your Solidity smart contract to the `contracts` folder.

2. Execute the fuzzer script:
    ```sh
    brownie run scripts/fuzzer.py
    ```

## Project Structure

- `contracts/` - Directory where your Solidity contracts should be placed.
- `scripts/` - Directory containing the fuzzer script.
- `requirements.txt` - Python dependencies for the project.
- `setting.sh` - Script to set up the environment.

## Example

1. Place a Solidity contract (e.g., `MyContract.sol`) into the `contracts` folder.

2. Run the fuzzer:
    ```sh
    brownie run scripts/fuzzer.py
    ```

The script will parse the contract using Slither, generate test cases, measure gas usage, and identify any abnormal gas usage patterns.

## Contributing

If you wish to contribute to this project, please fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Acknowledgments

- [Slither](https://github.com/crytic/slither) - Static analysis framework for Solidity.
- [Ganache](https://www.trufflesuite.com/ganache) - Personal blockchain for Ethereum development.
- [solc-select](https://github.com/crytic/solc-select) - Solidity compiler version switcher.
- [Brownie](https://eth-brownie.readthedocs.io/en/stable/) - Python-based development and testing framework for smart contracts.
