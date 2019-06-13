from bitcoinrpc.authproxy import AuthServiceProxy
from cryptoalpha.config import Config


def rpc_connect_node():
    # Official Bitcoin json rpc
    # https://www.jsonrpc.org/archive_json-rpc.org/python-json-rpc.html
    # Recommended fork
    # https://github.com/jgarzik/python-bitcoinrpc
    # rpc_user and rpc_password are set in the bitcoin.conf file
    # Run the following to set environment variables:
    # $ export RPCUSER=your_username
    # $ export RPCPASSWORD=your_password

    rpc_user = Config.RPCUSER
    rpc_password = Config.RPCPASSWORD
    url = 'http://'+rpc_user+':'+rpc_password+'@189.113.142.26:8332'
    rpc_connection = AuthServiceProxy(url)
    print("RPC Connection Created")
    best_block_hash = rpc_connection.getbestblockhash()
    print("Got best block hash")
    print(best_block_hash)
    best_block = (rpc_connection.getblock(best_block_hash))
    print("Got best block")
    print(best_block)

    # batch support : print timestamps of blocks 0 to 99 in 2 RPC round-trips:
    # commands = [["getblockhash", height] for height in range(100)]
    # block_hashes = rpc_connection.batch_(commands)
    # blocks = rpc_connection.batch_([["getblock", h] for h in block_hashes])
    # block_times = [block["time"] for block in blocks]

    return(best_block)
