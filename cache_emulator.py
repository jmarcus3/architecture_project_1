from math import log #as log
from collections import deque #as deque
import random
from sys import argv

################THIS CODE SNIPPET FOR COMMAND TAKING LINE ARGUMENTS CAME FROM################
################https://gist.github.com/dideler/2395703######################################

opts = {}  # Empty dictionary to store key-value pairs.
while argv:  # While there are arguments left to parse...
    if argv[0][0] == '-':  # Found a "-name value" pair.
        opts[argv[0]] = argv[1]  # Add key and value to the dictionary.
    argv = argv[1:]  # Reduce the argument list by copying it starting from index 1.

#############################################################################################
#############################################################################################

#block size:
if '-b' in opts:
    block_size_bytes = int(opts['-b']) 
else:
    block_size_bytes = 64 #default
print(f"block size: {block_size_bytes} bytes")

#cache size:
if '-c' in opts:
    cache_size_bytes = int(opts['-c'])
else:
    cache_size_bytes = 65536 #default
cache_size_blocks = int(cache_size_bytes/block_size_bytes)
print(f"cache size: {cache_size_bytes} bytes")
print(f"cache size: {cache_size_blocks} blocks")

#set size:
if '-n' in opts:
    blocks_per_set = int(opts['-n'])
else:
    blocks_per_set = 2 #default 
cache_size_sets = int(cache_size_blocks/blocks_per_set)
print(f"associativity: {blocks_per_set}")
print(f"number of sets in cache: {cache_size_sets} sets")

#replacement policy:
if '-r' in opts:
    replacement_policy = opts['-r']    
else:
    replacement_policy = 'LRU' #default
print(f"replacement policy: {replacement_policy}")

#algorithm:
if '-a' in opts:
    algorithm = opts['-a']
else:
    algorithm = 'mxm' #default
print(f"algorithm: {algorithm}")
print()
print()

#index, offset, and tag sizes:
index_size = int(log(cache_size_sets, 2))
offset_size = int(log(block_size_bytes, 2))
tag_size = 32 - index_size - offset_size



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
        self.instruction_count = 0

    def load_double(self, address):
        return self.cache.get_double(address)
        self.instruction_count += 1

    def store_double(self, address, double):
        self.cache.set_double(address, double)
        self.instruction_count += 1

    def add_double(self, value1, value2):
        return value1 + value2
        self.instruction_count += 1

    def mult_double(self, value1, value2):
        return value1 * value2
        self.instruction_count += 1

######################TEST ALGORITHMS###############################################

def dot_product(vector1, vector2, cpu):
    vector_length = len(vector1)
    address_array1 = []
    address_array2 = []
    address_array3 = []

    for i in range(vector_length):
        address_array1.append(Address(i * 8))
        cpu.store_double(address_array1[i], vector1[i])

    j = 0
    for i in range(vector_length, vector_length * 2):
        address_array2.append(Address(i * 8))    
        cpu.store_double(address_array2[j], vector2[j])
        j += 1

    for i in range(vector_length * 2, vector_length * 3):
        address_array3.append(Address(i * 8))

    for a, b, c in zip(address_array1, address_array2, address_array3):
        register1 = cpu.load_double(a)
        register2 = cpu.load_double(b)
        register3 = cpu.mult_double(register1, register2)
        cpu.store_double(c, register3)

    # solution = []
    # for c in address_array3:
    #     solution.append(cpu.load_double(c))

    # print(solution)

    print(f'total instructions: {cpu.instruction_count}')
    print(f'read_hits = {cpu.cache.read_hit}')
    print(f'write_hits = {cpu.cache.write_hit}')
    print(f'read_misses = {cpu.cache.read_miss}')
    print(f'write_misses = {cpu.cache.write_miss}')



def matrix_matrix(matrix1, matrix2, cpu):    
    matrix1_rows = len(matrix1)
    matrix1_columns = len(matrix1[0])
    matrix2_rows = len(matrix2)
    matrix2_columns = len(matrix2[0])

    address_matrix1 = []
    address_matrix2 = []
    address_matrix3 = []    
    
    a = 0

    for i in range(matrix1_rows):
        new = []
        address_matrix1.append(new)
        for j in range(matrix1_columns):
           address_matrix1[i].append(Address(a))
           cpu.store_double(address_matrix1[i][j], matrix1[i][j])
           a += 8

    for i in range(matrix2_rows):
        new = []
        address_matrix2.append(new)
        for j in range(matrix2_columns):
            address_matrix2[i].append(Address(a))
            cpu.store_double(address_matrix2[i][j], matrix2[i][j])
            a += 8

    for i in range(matrix1_rows):
        new = []
        address_matrix3.append(new)
        for j in range(matrix2_columns):
            address_matrix3[i].append(Address(a))
            cpu.store_double(address_matrix3[i][j], 0)
            a += 8


    for i in range(matrix1_rows):
        for j in range(matrix2_columns):
            register4 = 0
            for k in range(matrix1_columns):
                register1 = cpu.load_double(address_matrix1[i][k])
                register2 = cpu.load_double(address_matrix2[k][j])
                register3 = cpu.mult_double(register1, register2)
                register4 = cpu.add_double(register4, register3)
            cpu.store_double(address_matrix3[i][j], register4)

    # solution = []
    # for i in range(matrix1_rows):
    #     new = []
    #     solution.append(new)
    #     for j in range(matrix2_columns):
    #         solution[i].append(cpu.load_double(address_matrix3[i][j]))

    # print(solution)


    print(f'total instructions: {cpu.instruction_count}')
    print(f'read_hits = {cpu.cache.read_hit}')
    print(f'write_hits = {cpu.cache.write_hit}')
    print(f'read_misses = {cpu.cache.read_miss}')
    print(f'write_misses = {cpu.cache.write_miss}')


def do_block(si, sj, sk, address_matrix1, address_matrix2, address_matrix3, blocksize, cpu):
    for i in range(si, si+blocksize):
        for j in range(sj, sj + blocksize):
            cij = cpu.load_double(address_matrix3[i][j])
            for k in range(sk, sk+ blocksize):
                cij += cpu.mult_double(cpu.load_double(address_matrix1[i][k]), cpu.load_double(address_matrix2[k][j]))
            cpu.store_double(address_matrix3[i][j], cij)

def matrix_matrix_blocking(matrix1, matrix2, blocksize, cpu):    
    matrix1_rows = len(matrix1)
    matrix1_columns = len(matrix1[0])
    matrix2_rows = len(matrix2)
    matrix2_columns = len(matrix2[0])

    address_matrix1 = []
    address_matrix2 = []
    address_matrix3 = []    
    
    a = 0

    for i in range(matrix1_rows):
        new = []
        address_matrix1.append(new)
        for j in range(matrix1_columns):
           address_matrix1[i].append(Address(a))
           cpu.store_double(address_matrix1[i][j], matrix1[i][j])
           a += 8

    for i in range(matrix2_rows):
        new = []
        address_matrix2.append(new)
        for j in range(matrix2_columns):
            address_matrix2[i].append(Address(a))
            cpu.store_double(address_matrix2[i][j], matrix2[i][j])
            a += 8

    for i in range(matrix1_rows):
        new = []
        address_matrix3.append(new)
        for j in range(matrix2_columns):
            address_matrix3[i].append(Address(a))
            cpu.store_double(address_matrix3[i][j], 0)
            a += 8

    for sj in range(0, matrix1_rows, blocksize):
        for si in range(0, matrix1_rows, blocksize):
            for sk in range(0, matrix1_rows, blocksize):
                do_block(si, sj, sk, address_matrix1, address_matrix2, address_matrix3, blocksize, cpu)

    # solution = []
    # for i in range(matrix1_rows):
    #     new = []
    #     solution.append(new)
    #     for j in range(matrix2_columns):
    #         solution[i].append(cpu.load_double(address_matrix3[i][j]))

    # print(solution)

    print(f'total instructions: {cpu.instruction_count}')
    print(f'read_hits = {cpu.cache.read_hit}')
    print(f'write_hits = {cpu.cache.write_hit}')
    print(f'read_misses = {cpu.cache.read_miss}')
    print(f'write_misses = {cpu.cache.write_miss}')

############################MAIN##########################################################
def main():
    cpu = Cpu()

    if algorithm == 'dot':
        vector1 = []
        vector2 = []
        for a in range(0, 100000):
            vector1.append(random.randint(0,100))
            vector2.append(random.randint(0,100))
        dot_product(vector1, vector2, cpu)

    elif algorithm == 'mxm':
        matrix1 = []
        matrix2 = []
        x = 1 
        for i in range(16):
            new = []
            matrix1.append(new)
            for j in range(16):
                matrix1[i].append(x)
                x += 1
        for i in range(16):
            new = []
            matrix2.append(new)
            for j in range(16):
                matrix2[i].append(x)
                x += 1

        matrix_matrix(matrix1, matrix2, cpu)

    elif algorithm == 'mxm_block':
        matrix1 = []
        matrix2 = []
        x = 1 
        for i in range(128):
            new = []
            matrix1.append(new)
            for j in range(128):
                matrix1[i].append(x)
                x += 1
        for i in range(128):
            new = []
            matrix2.append(new)
            for j in range(128):
                matrix2[i].append(x)
                x += 1
        matrix_matrix_blocking(matrix1, matrix2, 32, cpu)

    else:
        raise ValueError('algorithm must be dot, mxm, or mxm_block')

    print(cpu.cache.cache)         

if __name__ == '__main__':
    main()
