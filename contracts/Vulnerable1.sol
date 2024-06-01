// contracts/Vulnerable.sol
pragma solidity ^0.8.0;

contract Vulnerable1 {
    uint256 amount;

    function test(uint256 _amount) public {
        if (_amount > 80000) {
            for (uint256 i = 0; i < _amount; i++) {
                amount+=1;
            }
        }
    }
}