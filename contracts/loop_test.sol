// contracts/loop_test.sol
pragma solidity ^0.8.0;

contract loop_test {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        for (uint256 i = 0; i < msg.value; i = i + 10) {
            balances[msg.sender] += 1;
        }        
    }

    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount, "Insufficient balance");
        (bool sent, ) = msg.sender.call{value: _amount}("");
        require(sent, "Failed to send Ether");
        balances[msg.sender] -= _amount;
    }
}