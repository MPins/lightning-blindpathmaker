# Overview
On Mar 28, 2023 the [lightning specification proposal](https://github.com/lightning/bolts/blob/master/proposals/route-blinding.md) for blinded paths was merged, which improves receiver privacy by replacing the recipient’s public key in invoices with a “blinded path” that obscures the receiver’s identity. Receiving nodes need to carefully select their blinded path to manage the tradeoff between privacy and reliability: providing more diverse blinded paths makes it easier to successfully make a payment, but it also reveals more information to a deanonymizing adversary. There are a number decisions a recipient can make in blinded path selection:
- Number of paths: how many blinded paths to the destination to provide.
- Path length: the number of hops (and fake “dummy” hops) in each blinded path.
- Introduction node(s): the cleartext node included in the blinded path, and whether to
select multiple distinct nodes.
- Fee/cltv aggregation: how much to aggregate (/round up) fees in the blinded path to
hide the actual channel policies from an adversary.
- Channel liquidity: size of the channels selected compared to the payment size (greater
ratio, greater reliability).

# The Project
This project is based on the Chaincode Hackaton Project Proposals done on first quarter of 2024 [here](https://github.com/MPins/lightning-blindpathmaker/blob/3ee9a8af3a3c2029ff32ea93116a435ce2437044/Hackathon_Project_-_Blinded_Path_Maker.pdf). The
“BlindedPathPathmaker” accepts a recipient public key and lightning graph and creates a blinded path(s) for the recipient to receive a specified payment amount. It provide also a user-friendly metric that captures the tradeoff between privacy and reliability, and use it to determine how to select paths.

Input format:
- Graph (json): a json description of the public graph.
- Amount (uint64): payment amount expressed in millisatoshis.
- Recipient (string): hex encoded public key of the receiving node.

Optional Input:
- Num Blinded Hops: the number of hops to use for each blinded path included in the invoice. (default=2)

Output a key/value list of possible recipients:
- A json representation of the blinded path(s) to use for the recipient
```
{
    "Introduction_node": "pubkey",
    "Anonymity" : "0",
    "Feasability" : "0",
    "Blinded_nodes": [“pubkey1”, “pubkey2”],
    "Nodes_channel": ["channel_id1", "channel_id2"]
    "Fee_base_msat": uint64,
    "Fee_rate_milli_msat": uint64,
    "Min_htlc": uint64,
    "Max_htlc_msat": unit64,
    "Time_lock_delta": uint32,
}
```
# The Metric
We are using two metrics to set the blinded path. 
The first one we call "Anonymity", this value represents the number of nodes that could feasibly be recipients for the blinded payment:
- They are within len(blinded hops) of the introduction node.
- The fee/cltv policy to reach the node is less than the aggregate reported by the blinded path

A trivial example of this metric is that a value of 1 would mean that the blinded path simply
selects the recipient as the introduction node and has no dummy hops - it is the only node that
could possibly be receiving this payment.

The second one we call "feasability", this value represents the size of the biggest payment possible trought the blinded path divided by the size of the invoice. 

A trivial example of this metric is that a value of 1 would mean that the blinded path simply
is as large as the invoice.

# How to Run
To run the Bind Path Maker is very simple, just clone the git repository on your machine.

```sh
git clone https://github.com/MPins/lightning-blindpathmaker
```

Go to the source folder and make sure you can run the blindpathmaker.py python program.

```sh
python blindpathmaker.py <json_file> <amount> <destination> <num_blinded_hops>
```

You can start using some json file examples on the graphs folder. The nodenamer will create the file blindepath.json in the current directory.