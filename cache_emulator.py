from math import log as log

#block size:
block_size_bytes = 64 #to take command line argument, default for now
print(f"block size is {block_size_bytes} bytes")

#cache size:
cache_size_bytes = 65536 #to take command line argument, default for now
cache_size_blocks = cache_size_bytes/block_size_bytes
print(f"cache size is {cache_size_bytes} bytes")
print(f"cache size is {cache_size_blocks} blocks")

#set size:
blocks_per_set = 1
print(f"number of blocks per set is {blocks_per_set}")
cache_size_sets = cache_size_blocks/blocks_per_set
print(f"cache size is {cache_size_sets} sets")

#index, offset, and tag sizes:
index_size = int(log(cache_size_sets, 2))
#print(f"index size is {index_size}")
offset_size = int(log(block_size_bytes/8, 2))
tag_size = 32 - index_size - offset_size

######################ADDRESS OBJECT################################################
#byte address
class Address:
    def __init__(self, address):
        binary_address = bin(address)[2:]
        if len(binary_address) < 32:
            padding = '0' * (32-len(binary_address))
        else:
            padding = ''
        self.address = padding + binary_address                 
        self.dec_address = address

    def get_offset(self):        
        return self.address[32-offset_size:32]


    def get_index(self):
        return self.address[32-offset_size-index_size:32-offset_size] 
        #bin(int((self.address//block_size_bytes) % cache_size_sets))[2:]

    def get_tag(self):
        return self.address[:tag_size]

    def get_decimal_address(self):
        return self.dec_address


class DataBlock:
    def __init__(self):
        self.block = {}
        for i in range(int(block_size_bytes/8)):
            bini = bin(i)[2:]
            if len(bini) < offset_size:
                padding = '0' * (offset_size - len(bini))
            else:
                padding = ''
            self.block[padding+bini] = None

    def set_data(self, address, data):
        offset = address.get_offset()
        self.block[offset] = data

    def get_data(self, address):
        offset = address.get_offset()
        return self.block[offset]

    def __repr__(self):
        return self.block.__repr__()

class Ram:
    def __init__(self):
        self.memory = {}

    def set_block(self, address, value):
        block_address = address.get_decimal_address()//block_size_bytes
        if block_address in self.memory:
            self.memory[block_address].set_data(address, value)
        else:
            block = DataBlock()
            block.set_data(address, value)
            self.memory[block_address] = block

    def get_block(self, address):
        block_address = address.get_decimal_address()//block_size_bytes
        if block_address not in self.memory:
            raise KeyError("Address has not been initialized in Ram")
        return self.memory[block_address]

    def __repr__(self):
        return self.memory.__repr__()




def main():
    a = Address(571)
    print(f"ram address is {a.address}")
    print(f"cache index is {a.get_index()}")
    print(f"offset is: {a.get_offset()}")
    print(f"tag is: {a.get_tag()}")

    #aa = Address(572)
    #b = Address(32154)
    #bb = Address(32155)

    #ram = Ram()
    #ram.set_block(a, 30)
    #ram.set_block(aa, 31)
    #ram.set_block(b, 21)
    #ram.set_block(bb, 25)
    #print(ram)



if __name__ == '__main__':
    main()
