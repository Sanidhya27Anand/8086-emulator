import re
from pprint import pprint

from emulator.assembler import to_decimal
from emulator.pipeline_units.bus_interface_unit import BIU
from emulator.pipeline_units.execution_unit import EU

class CPU(object):
    '''
    The CPU class of the 8086.'''
    
    def __init__(self, BIU: BIU, EU: EU) -> None:
        self.cycle_count = 0
        self.BIU = BIU
        self.EU = EU

    def iterate(self) -> None:
        '''
        The main loop of the CPU.
        
        Parameters
        ----------
        debug : bool, optional
            If True, the CPU will print out the state of the CPU at each clock cycle.
            The default is False.
        
        Returns
        -------
        None'''
        self.cycle_count += 1

        self.fetch_cycle()

        self.cycle_count += 1

        self.execute_cycle()

        
        self.print_state()
        self.EU.interrupt = False

    def fetch_cycle(self) -> None:
        '''
        The fetch cycle of the CPU. This is the first stage of the pipeline.
        '''
        self.BIU.run()
        pass

    def execute_cycle(self) -> None:
        '''
        The execute cycle of the CPU. This is the last stage of the pipeline.'''
        self.EU.run()
        pass
    
    def check_done(self) -> bool:
        '''
        Checks if the CPU has finished executing.
        
        Returns
        -------
        result : bool
            True if the CPU has finished executing, False otherwise.'''
        if self.EU.interrupt or self.EU.shutdown:
            return True
        return  self.BIU.instruction_queue.empty() and \
                not self.BIU.remaining_instruction()

    def show_regs(self) -> None:
        '''
        Prints out the registers of the CPU.
        
        Returns
        -------
        None'''
        for key, val in list(self.EU.reg.items())[:4]:
            print(key, '0x{:0>4x}'.format(val), end='   ')
        print()
        for key, val in list(self.EU.reg.items())[4:]:
            print(key, '0x{:0>4x}'.format(val), end='   ')
        print()
        for key, val in self.BIU.registers.items():
            print(key, '0x{:0>4x}'.format(val), end='   ')
        print()
        print('S ', self.EU.FR.sign, end='  ')
        print('Z', self.EU.FR.zero, end='   ')
        print('AC', self.EU.FR.auxiliary, end='  ')
        print('P', self.EU.FR.parity, end='   ')
        print('CY', self.EU.FR.carry, end='  ')
        print('O', self.EU.FR.overflow, end='   ')
        print('D ', self.EU.FR.direction, end='  ')
        print('I', self.EU.FR.interrupt, end='   ')
        print('T ', self.EU.FR.trap, end='  ')
        print()

    def show_memory(self, begin: int, end: int) -> None:
        '''
        Prints out the memory of the CPU.
        
        Parameters
        ----------
        begin : int
            The beginning address of the memory to be printed.
        end : int
            The ending address of the memory to be printed.
        
        Returns
        -------
        None'''
        pprint(self.BIU.memory.space[begin: end], compact=True)

    def print_state(self) -> None:
        '''
        Prints out the current state of the CPU.
        '''
        print("\nPipeline:")
        pprint(list(self.BIU.instruction_queue.queue))
        print("\nMemory of CS:IP:")
        self.show_memory(self.BIU.cs_ip, self.BIU.cs_ip + 10)
        print("\nMemory of DS:")
        self.show_memory(self.BIU.registers['DS']*16, self.BIU.registers['DS']*16 + 40)
        print("\nRegisters:")
        self.show_regs()
        print("\nIR:  ", self.EU.IR)
        print("Next:", self.BIU.next_ins)
        print('-' * 80)
    
    def print_end_state(self) -> None:
        '''
        Prints out the final state of the CPU.
        '''
        self.EU.print("Clock ended\n")
        self.EU.print(f"CPU ran a total of {self.cycle_count} clock cycles\n")