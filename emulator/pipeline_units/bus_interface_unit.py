import sys
import queue
from typing import Union

from emulator.assembler import Assembler
from emulator.memory import Memory

class BIU(object):

    def __init__(self, instruction_queue_size: int, exec_code: Assembler, memory: Memory) -> None:
        self.instruction_queue = queue.Queue(instruction_queue_size)
        
        self.registers = {
            'DS': int(exec_code.segment_address['DS'], 16),
            'CS': int(exec_code.segment_address['CS'], 16),
            'SS': int(exec_code.segment_address['SS'], 16),
            'ES': int(exec_code.segment_address['ES'], 16),
            'IP': int(exec_code.instr_ptr, 16)
        }
        self.pre_fetch_ip = self.registers['IP']
        self.memory = memory

    @property
    def cs_ip(self) -> int:
        '''
        Get the current instruction pointer.
        
        Returns
        -------
        result : int
            The current instruction pointer.
        '''
        return self.registers['CS'] * 16 + self.registers['IP']

    @property
    def cs_pre_ip(self) -> int:
        '''
        Get the previous instruction pointer.
        
        Returns
        -------
        result : int
            The previous instruction pointer.
        '''
        return self.registers['CS'] * 16 + self.pre_fetch_ip

    def read_byte(self, location: int) -> str:
        '''
        Read a byte from the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        
        Returns
        -------
        result : str
            The byte at the memory location.
        '''
        return self.memory.read_byte(location)

    def read_word(self, location: int) -> str:
        '''
        Read a word from the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        
        Returns
        -------
        result : str
            The word at the memory location.
        '''
        return self.read_byte(location + 1) + self.read_byte(location)

    def read_dword(self, location: int) -> str:
        '''
        Read a dword from the memory location.

        Parameters
        ----------
        location : int
            The memory location.
        
        Returns
        -------
        result : str
            The dword at the memory location.
        '''
        return self.read_byte(location + 3) + self.read_byte(location + 2) + \
               self.read_byte(location + 1) + self.read_byte(location)

    def write_byte(self, location: int, content: Union[int, list]) -> None:
        '''
        Write a byte to the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        content : Union[int]
            The content to write.
        
        Returns
        -------
        None
    '''
        if isinstance(content, int):
            content = [hex(content)]
        elif isinstance(content, list):
            pass
        else:
            raise Exception("Error in writing byte.")
        self.memory.write_byte(location, content)

    def write_word(self, location: int, content: Union[int, list]) -> None:
        '''
        Write a word to the memory location.
        
        Parameters
        ----------
        location : int
            The memory location.
        content : Union[int]
            The content to write.
        
        Returns
        -------
        None
        '''
        if isinstance(content, int):
            self.write_byte(location, content & 0x0ff)
            self.write_byte(location + 1, (content >> 8) & 0x0ff)
        elif isinstance(content, list):
            for res in content:
                self.write_byte(location, [res])
                location += 1
        else:
            raise Exception("Error in writing word.")

    def write_dword(self, location: int, content: int) -> None:
        if isinstance(content, int):
            self.write_byte(location, content & 0x0ff)
            self.write_byte(location + 1, (content >> 8) & 0x0ff)
            self.write_byte(location + 2, (content >> 16) & 0x0ff)
            self.write_byte(location + 3, content >> 24)
        else:
            raise Exception("Error in writing dword.")

    def run(self) -> None:
        '''
        Run the BIU.
        
        Returns
        -------
        None
        '''
        if self.instruction_queue.qsize() <= self.instruction_queue.maxsize - 2:
            self.fill_instruction_queue()

    @property
    def next_ins(self) -> str:
        '''
        Get the next instruction.
        
        Returns
        -------
        result : str
            The next instruction.'''
        ins_list = list(self.instruction_queue.queue)
        if ins_list:
            return ins_list[0]
        else:
            return "Pipeline is empty."

    def flush_pipeline(self) -> None:
        '''
        Flush the pipeline.
        
        Returns
        -------
        None
        '''
        self.instruction_queue.queue.clear()
        self.pre_fetch_ip = self.registers['IP']

    def remaining_instruction(self) -> bool:
        '''
        Check if the instruction queue is empty.
        
        Returns
        -------
        result : bool
            True if the instruction queue is not empty.'''
        return not self.memory.is_null(self.cs_pre_ip)

    def fetch_one_instruction(self) -> None:
        '''
        Fetch one instruction.

        Returns
        -------
        None
        '''
        instruction = self.memory.read_byte(self.cs_pre_ip)
        self.instruction_queue.put(instruction)
        self.pre_fetch_ip += 1

    def fill_instruction_queue(self) -> None:
        '''
        Fills the instruction queue.
        
        Returns
        -------
        None
        '''
        while not self.instruction_queue.full():
            if not self.memory.is_null(self.cs_pre_ip):
                self.fetch_one_instruction()
            else:
                break
