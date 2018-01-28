from math import log as log
from collections import deque as deque
import random

#block size:
block_size_bytes = 64 #to take command line argument, default for now
#print(f"block size is {block_size_bytes} bytes")

#cache size:
cache_size_bytes = 65536 #to take command line argument, default for now
cache_size_blocks = cache_size_bytes/block_size_bytes
#print(f"cache size is {cache_size_bytes} bytes")
#print(f"cache size is {cache_size_blocks} blocks")

#set size:
blocks_per_set = 2
#print(f"number of blocks per set is {blocks_per_set}")
cache_size_sets = int(cache_size_blocks/blocks_per_set)
#print(f"cache size is {cache_size_sets} sets")

#index, offset, and tag sizes:
index_size = int(log(cache_size_sets, 2))
offset_size = int(log(block_size_bytes, 2))
tag_size = 32 - index_size - offset_size

#replacement policy:
replacement_policy = 'LRU'

######################ADDRESS CLASS################################################
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

######################DATA CLASS######################################

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

#####################RAM CLASS###################################

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
            self.set_block(address, None)
        return self.memory[block_address]

    def __repr__(self):
        return self.memory.__repr__()

####################CACHE CLASS##################################

class Cache:
    def __init__(self, ram):
        self.cache = {}
        self.lru_cache = {}
        self.read_hit = 0
        self.write_hit = 0
        self.read_miss = 0
        self.write_miss = 0
        self.ram = ram
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

    def set_double(self, address, double):
        index = address.get_index()
        tag = address.get_tag()
        hit = False #flag if cache search was a hit
        for slot, block in enumerate(self.cache[index]):
            if block != None and tag in block:
                self.write_hit += 1
                hit = True
                self.ram.set_block(address, double) #writes cache and ram
                if replacement_policy == 'LRU':
                    self._lru_update(index, slot) #updates lru with recently used slot
        if hit == False:
            self.write_miss += 1
            self._replace(address, index, tag)
            self.ram.set_block(address, double) #writes cache and ram

    def _replace(self, address, index, tag):
        block_address = address.get_decimal_address()//block_size_bytes
        
        if None in self.cache[index] and replacement_policy != 'FIFO':
            open_slot = self.cache[index].index(None)
            self.cache[index][open_slot] = {tag:self.ram.get_block(address)}
            if replacement_policy == 'LRU':
                self._lru_update(index, open_slot)
        
        elif replacement_policy == 'FIFO':
            self.cache[index].append({tag:self.ram.get_block(address)}) #should enque FIFO style
        
        elif None not in self.cache[index] and replacement_policy == 'LRU':
            last_used_time = 0
            last_used_slot = 0
            for slot_num, slot in enumerate(self.lru_cache[index]):
                if slot > last_used_time:
                    last_used_time = slot
                    last_used_slot = slot_num
            self.cache[index][last_used_slot] = {tag:self.ram.get_block(address)}
            self._lru_update(index, last_used_slot)

        elif None not in self.cache[index] and replacement_policy == 'RANDOM':
            self.cache[index][random.randint(0, blocks_per_set - 1)] = {tag:self.ram.get_block(address)}


    def _lru_update(self, index, just_used):
        for lru_slot, lru_block in enumerate(self.lru_cache[index]):
            self.lru_cache[index][lru_slot] += 1
        self.lru_cache[index][just_used] = 0

    def get_double(self, address):
        index = address.get_index()
        tag = address.get_tag()
        for slot, block in enumerate(self.cache[index]):
            if block != None and tag in block:
                self.read_hit += 1
                if replacement_policy == 'LRU':
                    self._lru_update(index, slot)
                return self.ram.get_block(address).get_data(address)
        self.read_miss += 1
        self._replace(address, index, tag)
        return self.ram.get_block(address).get_data(address)

###########################CPU CLASS###################################

class Cpu:
    def __init__(self):
        ram = Ram()
        self.cache = Cache(ram)

    def load_double(self, address):
        return self.cache.get_double(address)

    def store_double(self, address, double):
        self.cache.set_double(address, double)

    def add_double(self, address1, address2):
        return self.load_double(address1) + self.load_double(address2)

    def mult_double(self, address1, address2):
        return self.load_double(address1) * self.load_double(address2)


def main():
    cpu = Cpu()
    address_array1 = [] #takes array of addresses
    address_array2 = [] #takes different array of addresses
    address_array3 = [] #takes array of address for dot products
    
    #loading doubles:
    for a in range(0, 100000, 8):
        address = Address(a)
        address_array1.append(address)
        cpu.store_double(address, random.randint(0,20))
    for b in range(100000, 200000, 8):
        address = Address(b)
        address_array2.append(address)
        cpu.store_double(address, random.randint(0, 20))
    for c in range(200000, 300000, 8):
        address = Address(c)
        address_array3.append(address)

    #dot product:
    for i, a in enumerate(address_array1):
        cpu.store_double(address_array3[i], cpu.mult_double(a, address_array2[i]))
        
    print(f'read_hits = {cpu.cache.read_hit}')
    print(f'write_hits = {cpu.cache.write_hit}')
    print(f'read_misses = {cpu.cache.read_miss}')
    print(f'write_misses = {cpu.cache.write_miss}')



    """a = Address(0)
    #print("for address 0")
    #print(f"ram address is {a.address}")
    #print(f"cache index is {a.get_index()}")
    #print(f"offset is: {a.get_offset()}")
    #print(f"tag is: {a.get_tag()}")
  

    block = DataBlock()
    #print(block)

    aa = Address(8)
    aaa = Address(16)
    aaaa = Address(24)
    b = Address(4096)
    bb = Address(4104)
    cc = Address(65536)
    dd = Address(65536*2)

    ram = Ram()
    #ram.set_block(a, 1)
    #print(ram.get_block(a))
    #ram.set_block(aa, 2)
    #ram.set_block(aaa, 3)
    #ram.set_block(aaaa, 4)
    #ram.set_block(b, 64)
    #ram.set_block(bb,72)
    #print(ram)

    cache = Cache(ram)
    cache.set_double(a, 3)
    cache.set_double(a, 4)
    cache.set_double(aa, 5)
    cache.set_double(cc, 1)
    cache.set_double(dd, 999)

    cpu = Cpu(cache, ram)
    print(cache.cache['000000000'])
    print(f'write hits: {cache.write_hit}')
    print(f'write misses: {cache.write_miss}')
    print(f'get address 0: {cache.get_double(a)}')
    print(cache.cache['000000000'])
    print(f'read hits: {cache.read_hit}')
    print(f'read miss: {cache.read_miss}')
    print(f'4+5: {cpu.add_double(a, aa)}')
    #print(cache.cache)
    #print(f"lru_cache: {cache.lru_cache['000000000']}")"""

if __name__ == '__main__':
    main()
