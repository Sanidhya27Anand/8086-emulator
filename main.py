import sys
import getopt

from emulator.assembler import Assembler
from emulator.memory import Memory
from emulator.pipeline_units.bus_interface_unit import BIU
from emulator.pipeline_units.execution_unit import EU
from emulator.cpu import CPU

# constants
INSTRUCTION_QUEUE_SIZE = 6
MEMORY_SIZE = int('FFFFF', 16)
CACHE_SIZE = int('10000', 16)
SEGMENT_SIZE = int('10000', 16) 

INIT_SEGMENTS = {
    'DS': int('2000', 16),
    'CS': int('3000', 16),
    'SS': int('5000', 16),
    'ES': int('7000', 16) 
}


def main() -> None:
    '''
    The main function.
    '''
    help_str = '''
    8086 Emulator: an emulator for the Intel's 8086 CPU.
    Usage:
        python main.py <input_file> [options]
    Options:
        -h, --help: show this help message and exit
        -i, --interrupts: show interrupts
    '''

    INTERRUPT_MSG = False       # show interrupt messages
    try:
        # parse command line arguments
        opts, args = getopt.getopt(
            sys.argv[1:],
            '-h-i',
            ['help','interrupt']
        )
        for opt_name, _ in opts:
            if opt_name in ('-h','--help'):
                print(help_str)
                exit()
            if opt_name in ('-i', '--interrupts'):
                INTERRUPT_MSG = True
        with open(args[0], 'r', encoding='utf-8') as f:
            code = f.read()
    except:
        print(help_str)
        sys.exit("Incorrect arguments.")
   
    assembler = Assembler(INIT_SEGMENTS)            # intialize the assembler
    exe_file = assembler.compile(code)              # compile the code
    memory = Memory(MEMORY_SIZE, SEGMENT_SIZE)      # initialize the memory
    memory.load(exe_file)                           # load the code into the memory

    biu = BIU(INSTRUCTION_QUEUE_SIZE, exe_file, memory)   # initialize the bus interface unit
    eu = EU(biu, INTERRUPT_MSG)                                  # initialize the execution unit
    cpu = CPU(biu, eu)                                                      # initialize the CPU
    print("\nCPU initialized successfully.")
    print("=" * 50)

    # run the CPU
    while not cpu.check_done():
        cpu.iterate()
    cpu.print_end_state()

if __name__ == "__main__":
    main()