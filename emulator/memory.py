from emulator.assembler import Assembler


class Memory(object):
    '''
    The memory of the 8086 CPU.
    '''
    def __init__(self, max_space: int, seg_size: int) -> None:
        self.max_space = max_space              # maximum space of the memory (1 MB)
        self.seg_size = seg_size                # size of each segment
        self.space = [['0']] * self.max_space   # memory space

    def is_null(self, location: int) -> bool:
        '''
        Check if the memory location is null.
        
        Parameters
        ----------
        location : int
            The memory location.
        
        Returns
        -------
        result : bool
            True if the memory location is null, False otherwise.'''
        return self.space[location] == ['0']

    def verify(self, location: int) -> None:
        '''
        Verify if the memory location is valid.
        
        Parameters
        ----------
        location : int
            The memory location.
        '''
        if location < 0 or location > self.max_space:
            raise Exception(f"Invalid memory location: {location}.")

    def read_byte(self, location: int) -> str:
        '''
        Read the content of the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        
        Returns
        -------
        result : str
            The content of the memory location.'''
        self.verify(location)
        return self.space[location]

    def write_byte(self, location: int, content: str) -> None:
        '''
        Write the content to the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        content : str
            The content to be written.
        
        Returns
        -------
        None'''
        self.verify(location)
        self.space[location] = content
        
    def load(self, exec_code: Assembler) -> None:
        '''
        Load the code into the memory.
        
        Parameters
        ----------
        exec_code : Assembler
            The code to be loaded.
        
        Returns
        -------
        None'''
        self.refresh()
        print("Loading assembly code to memory...")
        for seg, val in exec_code.space.items():
            adr = int(exec_code.segment_address[seg], 16) * 16
            print(hex(adr))
            self.space[adr: adr + self.seg_size] = val
            print(self.space[adr:adr+100])
        load_isr(self)
        print("Loading successful!\n")
        
    def refresh(self) -> None:
        '''
        Refresh the memory.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None'''
        self.space = [['0']] * self.max_space


SEG_INIT = {
    'DS': int('0000', 16), # Initial value of data segment
    'CS': int('1000', 16), # Initial value of code segment
    'SS': int('0000', 16), # Initial value of stack segment
    'ES': int('0000', 16) # Initial value of extra segment
}



def load_ivt(memory: Memory) -> None:
    '''
    Loads the interrupt vector table into memory.
    
    Parameters
    ----------
    memory: Memory
        The memory object to load the interrupt vector table into.
    
    Returns
    -------
    None'''
    for i in range(256):
        memory.write_byte(i * 4, ['0x00'])
        memory.write_byte(i * 4 + 1, ['0x00'])
        memory.write_byte(i * 4 + 2, [str(hex(i % 16)) + '0'])  # CS
        memory.write_byte(i * 4 + 3, ['0x1' + str(hex(i // 16))[-1]])

def load_isr(memory: Memory) -> None:
    '''
    Loads the interrupt service routine into memory.
    
    Parameters
    ----------
    memory: Memory
        The memory object to load the interrupt service routine into.
    
    Returns
    -------
    None'''
    load_ivt(memory)
    print("Loading Interrupt Service Routine...")

    for i in ['0', '1', '2', '3', '4', '7c']:
        assembler = Assembler(SEG_INIT)
        with open("./tests/Interrupt/isr" + i + ".asm", 'r', encoding='utf-8') as file:
            asm_code = file.read()
        isr = assembler.compile(asm_code)
        length = isr.segment_length['CS']
        base = (int('1000', 16) << 4) + int('100', 16) * int('0x'+i, 16)
        memory.space[base : base + length] = isr.space['CS'][:length]