// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Auction {
    struct Bid {
        address bidder;
        uint256 amount;
    }

    address public owner;
    Bid[] public bids;
    uint256 public auctionEndTime;
    bool public ended;

    event AuctionEnded(address winner, uint256 amount);

    constructor(uint256 _biddingTime) {
        owner = msg.sender;
        auctionEndTime = block.timestamp + _biddingTime;
    }

    function placeBid() public payable {
        require(block.timestamp <= auctionEndTime, "Auction already ended.");
        require(msg.value > 0, "Bid amount must be greater than zero.");

        // Record the bid
        bids.push(Bid({
            bidder: msg.sender,
            amount: msg.value
        }));
    }

    function endAuction() public {
        require(block.timestamp >= auctionEndTime, "Auction not yet ended.");
        require(!ended, "Auction already ended.");

        // Find the highest bid
        uint256 highestBid = 0;
        address highestBidder;

        for (uint256 i = 0; i < bids.length; i++) {
            if (bids[i].amount > highestBid) {
                highestBid = bids[i].amount;
                highestBidder = bids[i].bidder;
            }
        }

        ended = true;
        emit AuctionEnded(highestBidder, highestBid);

        // Transfer the highest bid amount to the owner
        payable(owner).transfer(highestBid);
    }

    function getBidsCount() public view returns (uint256) {
        return bids.length;
    }
}