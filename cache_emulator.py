from math import log as log
from collections import deque as deque

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
cache_size_sets = int(cache_size_blocks/blocks_per_set)
print(f"cache size is {cache_size_sets} sets")

#index, offset, and tag sizes:
index_size = int(log(cache_size_sets, 2))
offset_size = int(log(block_size_bytes, 2))
tag_size = 32 - index_size - offset_size

#replacement policy:
replacement_policy = 'LRU'

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

######################DATA BLOCK OBJECT######################################

class DataBlock:
    def __init__(self):
        self.block = {}
        for i in range(0,block_size_bytes,8):
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

#####################RAM OBJECT###################################

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

####################CACHE OBJECT##################################

class Cache:
    def __init__(self):
        self.cache = {}
        self.lru_cache = {}
        self.read_hit = 0
        self.write_hit = 0
        self.read_miss = 0
        self.write_miss = 0
        for i in range(cache_size_sets):
            bini = bin(i)[2:]
            if len(bini) < index_size:
                padding = '0' * (index_size - len(bini))
            else:
                padding = ''
            if replacement_policy == 'FIFO':
                self.cache[padding+bini] = deque([],blocks_per_set)
            elif replacement_policy == 'LRU': 
                self.cache[padding+bini] = [None] * blocks_per_set
                self.lru_cache[padding+bini] = [0] * blocks_per_set                
            elif replacement_policy == 'RANDOM':
                self.cache[padding+bini] = [None] * blocks_per_set
            else:
                raise ValueError('Replacement policy must be FIFO, LRU, or RANDOM')

    def set_double(self, address, double, ram):
        index = address.get_index()
        tag = address.get_tag()
        if tag in self.cache[index]:
            self.write_hit += 1
            for slot, block in enumerate(self.cache[index]):
                if block == tag: ##########This is probably jank#########
                    block[address.get_offset()] = double
                    if replacement_policy == 'LRU':
                        for lru_slot, lru_block in enumerate(self.lru_cache[index]):
                            self.lru_cache[index][lru_slot] += 1
                            if lru_slot == slot:
                                self.lru_cache[index][lru_slot] = 0
        else:
            self.write_miss += 1
            self._replace(address, double, ram)

    def _replace(self, address, double, ram):
        pass




def main():
    a = Address(0)
    print("for address 0")
    print(f"ram address is {a.address}")
    print(f"cache index is {a.get_index()}")
    print(f"offset is: {a.get_offset()}")
    print(f"tag is: {a.get_tag()}")
  

    block = DataBlock()
    #print(block)

    aa = Address(8)
    aaa = Address(16)
    aaaa = Address(24)
    b = Address(4096)
    bb = Address(4104)

    ram = Ram()
    ram.set_block(a, 1)
    ram.set_block(aa, 2)
    ram.set_block(aaa, 3)
    ram.set_block(aaaa, 4)
    ram.set_block(b, 64)
    ram.set_block(bb,72)
    #print(ram)

    cache = Cache()
    #print(cache.cache)

if __name__ == '__main__':
    main()
