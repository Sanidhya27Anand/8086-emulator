import sys
import re
import datetime

from emulator.pipeline_units.bus_interface_unit import BIU
from emulator.flag_register import FlagRegister
from emulator.instructions import *
from emulator.assembler import to_decimal


class EU(object):

    def __init__(self, BIU: BIU, int_msg: bool) -> None:
        self.IR = []                # Instruction Register
        self.opcode = ''            # Opcode
        self.opd = []               # Operands
        self.opbyte = 2             # Opcode byte
        self.eo = [0] * 5           # EO register
        self.bus = BIU              # Bus interface unit
        self.interrupt = False      # Interrupt flag
        self.shutdown = False       # Shutdown flag
        self.int_msg = int_msg      # Interrupt message
        self.FR = FlagRegister()   # Flag register
        self.reg = {                # General purpose registers
            'AX': 0,
            'BX': 0,
            'CX': 0,
            'DX': 0,
            'SP': 0,
            'BP': 0,
            'SI': 0,
            'DI': 0
        }
        self.eu_regs = list(self.reg.keys()) + ['AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH']     # EU registers
        self.biu_regs = list(BIU.registers.keys())                                                        # BIU registers
        self.output = ''                                                                            # Output string

    def print(self, string: str) -> None:
        '''
        Prints the string to the output string.
        
        Parameters
        ----------
        string : str
            String to be printed.
        
        Returns
        -------
        None'''
        print(string, end='')

        self.output += string

    def run(self) -> None:
        '''
        Runs the EU.
        
        Returns
        -------
        None'''
        self.IR = self.bus.instruction_queue.get()
        self.opcode = self.IR[0]
        self.bus.registers['IP'] += 1                             
        self.opd = []
        if len(self.IR) > 1:
            self.opd = self.IR[1:]
        self.get_opbyte()
        self.control_circuit()

    def get_opbyte(self) -> None:
        '''
        Gets the opcode byte.
        
        Returns
        -------
        None'''
        self.opbyte = 2
        for pr in self.opd:
            if pr in ['AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH']:
                self.opbyte = 1
        if 'PTR' in self.opd:
            self.opd.remove('PTR')
            if 'BYTE' in self.opd:
                self.opbyte = 1
                self.opd.remove('BYTE')
            elif 'WORD' in self.opd:
                self.opbyte = 2
                self.opd.remove('WORD')
            elif 'DWORD' in self.opd:
                self.opbyte = 4
                self.opd.remove('DWORD')
            else:
                sys.exit("Runtime Error: Unexpected PTR")
        if self.opcode in string_manipulation_instr:
            if 'B' in self.opcode:
                self.opbyte = 1
            else:
                self.opbyte = 2

    def read_reg(self, reg: str) -> int:
        '''
        Reads the value of a register.
        
        Parameters
        ----------
        reg : str
            Register to be read.
        
        Returns
        -------
        value : int
            Value of the register.
        '''
        if reg in self.biu_regs:
            res = self.bus.registers[reg]
        elif reg[1] == 'H':
            res = (self.reg[reg.replace('H', 'X')] >> 8) & 0xff
        elif reg[1] == 'L':
            res = self.reg[reg.replace('L', 'X')] & 0xff
        else:
            res = self.reg[reg]
        return res

    def write_reg(self, reg: str, num: int) -> None:
        '''
        Writes the value to a register.
        
        Parameters
        ----------
        reg : str
            Register to be written to.
        num : int
            Value to be written.
        
        Returns
        -------
        None'''
        num = self.to_unsigned(num) & 0xffff
        if reg in self.biu_regs:
            self.bus.registers[reg] = num
        elif reg[1] == 'H':
            reg = reg.replace('H', 'X')
            self.reg[reg] = (self.reg[reg] & 0xff) + ((num & 0xff) << 8)
        elif reg[1] == 'L':
            reg = reg.replace('L', 'X')
            self.reg[reg] = (self.reg[reg] & 0xff00) + (num & 0xff)
        else:
            self.reg[reg] = num

    def inc_reg(self, reg: str, val: int) -> None:
        '''
        Increments a register.
        
        Parameters
        ----------
        reg : str
            Register to be incremented.
        val : int
            Value to be added to the register.
        
        Returns
        -------
        None'''
        self.write_reg(reg, self.read_reg(reg) + val)

    def get_address(self, opd: str) -> int:
        '''
        Gets the address of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        address : int
            Address of the operand.
        '''
        adr_reg = ['BX', 'SI', 'DI', 'BP']
        seg_reg = ['DS', 'CS', 'SS', 'ES']
        par_list = [s for s in re.split('\W', opd) if s]
        address = 0
        has_seg = False
        for par in par_list:
            if par in adr_reg:
                address += self.read_reg(par)
            elif par in seg_reg:
                address += self.read_reg(par) << 4
                has_seg = True
            else:
                address += to_decimal(par)
        if not has_seg:
            if 'BP' in par_list:
                address += self.read_reg('SS') << 4
            else:
                address += self.read_reg('DS') << 4
        return address

    def get_offset(self, opd: str) -> int:
        '''
        Gets the offset of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        offset : int
            Offset of the operand.
        '''
        adr_reg = ['BX', 'SI', 'DI', 'BP']
        seg_reg = ['DS', 'CS', 'SS', 'ES']
        opd = opd.split(':')[-1]
        par_list = [s for s in re.split('\W', opd) if s]
        offset = 0
        for par in par_list:
            if par in adr_reg:
                offset += self.read_reg(par)
            elif par in seg_reg:
                pass
            else:
                offset += to_decimal(par)
        return offset

    def __get_byte(self, opd: str) -> int:
        '''
        Gets the byte of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        byte : int
            Byte of the operand.'''
        address = self.get_address(opd)
        content = self.bus.read_byte(address)
        return content

    def __get_word(self, opd: str) -> int:
        '''
        Gets the word of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        word : int
            Word of the operand.'''
        address = self.get_address(opd)
        content = self.bus.read_word(address)
        return content

    def __get_dword(self, opd: str) -> int:
        '''
        Gets the dword of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        dword : int
            Dword of the operand.'''
        address = self.get_address(opd)
        content = self.bus.read_dword(address)
        return content

    def __get_char(self, address: int) -> str:
        '''
        Gets the character of an address.
        
        Parameters
        ----------
        address : int
            Address of the character.
        
        Returns
        -------
        char : str
            Character of the address.'''
        return chr(to_decimal(self.bus.read_byte(address)[0]))

    def get_int(self, opd: str) -> int:
        '''
        Gets the integer of an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be read.
        
        Returns
        -------
        int : int
            Integer of the operand.'''
        if isinstance(opd, int):
            opd = '[' + str(opd) + ']'
        if self.is_reg(opd):
            res = self.read_reg(opd)
        elif '[' in opd:
            if self.opbyte == 1:
                res_list = self.__get_byte(opd)
            elif self.opbyte == 2:
                res_list = self.__get_word(opd)
            elif self.opbyte == 4:
                res_list = self.__get_dword(opd)
            else:
                sys.exit("Opbyte Error")
            res = 0
            assert res_list, "Empty memory space"

            for num in res_list:
                res = (res << 8) + (int(num, 16) & 0xff)
        else:
            res = to_decimal(opd)
        return res

    def get_int_from_adr(self, adr: int) -> int:
        '''
        Gets the integer of an address.
        
        Parameters
        ----------
        adr : int
            Address of the integer.
        
        Returns
        -------
        int : int
            Integer of the address.'''
        if self.opbyte == 1:
            res_list = self.bus.read_byte(adr)
        elif self.opbyte == 2:
            res_list = self.bus.read_word(adr)
        elif self.opbyte == 4:
            res_list = self.bus.read_dword(adr)
        else:
            sys.exit("Opbyte Error")
        res = 0
        assert res_list, "Empty memory space"
        for num in res_list:
            res = (res << 8) + (int(num, 16) & 0xff)
        return res

    def put_int(self, opd: str, num: int) -> None:
        '''
        Puts the integer into an operand.
        
        Parameters
        ----------
        opd : str
            Operand to be written.
        num : int
            Integer to be written.
        
        Returns
        -------
        None
        '''
        if self.is_reg(opd):
            self.write_reg(opd, num)
        elif self.is_mem(opd):
            adr = self.get_address(opd)
            self.write_mem(adr, num)

    def is_reg(self, opd: str) -> bool:
        '''
        Checks if the operand is a register.
        
        Parameters
        ----------
        opd : str
            Operand to be checked.
        
        Returns
        -------
        is_reg : bool
            True if the operand is a register.'''
        return opd in (self.eu_regs + self.biu_regs)

    def is_mem(self, opd: str) -> bool:
        '''
        Checks if the operand is a memory address.
        
        Parameters
        ----------
        opd : str
            Operand to be checked.
        
        Returns
        -------
        is_mem : bool
            True if the operand is a memory address.'''
        return '[' in opd

    def write_mem(self, loc: int, content: int) -> None:
        '''
        Writes the content into a memory address.
        
        Parameters
        ----------
        loc : int
            Address of the content.
        content : int
            Content to be written.
        
        Returns
        -------
        None'''
        if self.opbyte == 1:
            self.bus.write_byte(loc, content)
        elif self.opbyte == 2:
            self.bus.write_word(loc, content)
        elif self.opbyte == 4:
            self.bus.write_dword(loc, content)
        else:
            sys.exit("Opbyte Error")

    def control_circuit(self) -> None:
        '''
        Controls the circuit.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
        
        Instruction Types
        -----------------
        1. Data Transfer Instructions
        2. Arithmetic Instructions
        3. Logical Instructions
        4. Shift Instructions
        5. Branch Instructions
        6. String Instructions
        7. Flag Instructions
        8. Stack Instructions
        9. I/O Instructions
        10. Miscellaneous Instructions'''
        print(self.opcode)
        old_cs_ip = self.bus.cs_ip
        if self.opcode in data_transfer_instr:
            self.data_transfer_ins()
        elif self.opcode in arithmetic_instr:
            self.arithmetic_ins()
        elif self.opcode in logical_instr:
            self.logical_ins()
        elif self.opcode in rotate_shift_instr:
            self.rotate_shift_ins()
        elif self.opcode in transfer_control_instr:
            self.transfer_control_ins()
        elif self.opcode in string_manipulation_instr:
            self.string_manipulation_ins()
        elif self.opcode in flag_manipulation_instr:
            self.flag_manipulation_ins()
        elif self.opcode in stack_related_instr:
            self.stack_related_ins()
        elif self.opcode in input_output_instr:
            self.input_output_ins()
        elif self.opcode in miscellaneous_instr:
            self.miscellaneous_ins()
        else:
            sys.exit("operation code not support")
        if old_cs_ip != self.bus.cs_ip:
            self.bus.flush_pipeline()

    def data_transfer_ins(self) -> None:
        '''
        Data Transfer Instructions
        --------------------------
        Instructions related to data transfer in the microprocessor.
        1. MOV: Moves data from one operand to another.
        2. XCHG: Exchanges data between two operands.
        3. LEA: Load Effective Address.
        4. LDS: Loads the DS register.
        5. LES: Loads the ES register.'''
        self.opd[1] = ''.join(self.opd[1:])
        if self.opcode == 'MOV':
            res = self.get_int(self.opd[1])
            self.put_int(self.opd[0], res)

        elif self.opcode == 'XCHG':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            self.put_int(self.opd[0], res2)
            self.put_int(self.opd[1], res1)

        elif self.opcode == 'LEA':
            adr = self.get_offset(self.opd[1])
            self.put_int(self.opd[0], adr)

        elif self.opcode == 'LDS':
            adr = self.get_address(self.opd[1])
            self.write_reg(self.opd[0], self.get_int(adr))
            self.write_reg('DS', self.get_int(adr + 2))

        elif self.opcode == 'LES':
            adr = self.get_address(self.opd[1])
            self.write_reg(self.opd[0], self.get_int(adr))
            self.write_reg('ES', self.get_int(adr + 2))
        else:
            pass

    def popcount(self, num: int) -> int:
        '''
        Counts the number of 1s in a number.
        
        Parameters
        ----------
        num : int
            Number to be counted.
        
        Returns
        -------
        popcount : int
            Number of 1s in the number.'''
        cnt = 0
        while num > 0:
            cnt += 1
            num &= num - 1
        return cnt

    def to_signed(self, num: int) -> int:
        '''
        Converts a number to a signed number.
        
        Parameters
        ----------
        num : int
            Number to be converted.
        
        Returns
        -------
        signed_num : int
            Signed number.'''
        result = 0
        for i in range(self.opbyte * 8):
            if i == self.opbyte * 8 - 1:
                result -= (num >> i & 1) << i
            else:
                result += (num >> i & 1) << i
        return result

    def to_unsigned(self, num: int) -> int:
        '''
        Converts a number to an unsigned number.
        
        Parameters
        ----------
        num : int
            Number to be converted.
        
        Returns
        -------
        unsigned_num : int
            Unsigned number.'''
        result = 0
        for i in range(self.opbyte * 8):
            result += (num >> i & 1) << i
        return result

    def is_overflow(self, num: int) -> bool:
        '''
        Checks if the number is overflowed.
        
        Parameters
        ----------
        num : int
            Number to be checked.
        
        Returns
        -------
        is_overflow : bool
            True if the number is overflowed.'''
        low = self.to_signed(int('1' + (self.opbyte * 8 - 1) * '0', 2))
        high = self.to_signed(int('0' + (self.opbyte * 8 - 1) * '1', 2))
        return num > high or num < low

    def set_pf(self, result: int) -> None:
        '''
        Sets the Parity flag.
        
        Parameters
        ----------
        result : int
            Result of the operation.
        
        Returns
        -------
        None'''
        if self.popcount(result) % 2 == 0:
            self.FR.parity = 1
        else:
            self.FR.parity = 0

    def set_of(self, result: int) -> None:
        '''
        Sets the Overflow flag.
        
        Parameters
        ----------
        result : int
            Result of the operation.
        
        Returns
        -------
        None'''
        if self.is_overflow(result):
            self.FR.overflow = 1
        else:
            self.FR.overflow = 0

    def set_sf(self, result: int) -> None:
        '''
        Sets the Sign flag.
        
        Parameters
        ----------
        result : int
            Result of the operation.
        
        Returns
        -------
        None'''
        if self.to_signed(result) < 0:
            self.FR.sign = 1
        else:
            self.FR.sign = 0

    def set_zf(self, result: int) -> None:
        '''
        Sets the Zero flag.
        
        Parameters
        ----------
        result : int
            Result of the operation.
        
        Returns
        -------
        None'''
        if result == 0:
            self.FR.zero = 1
        else:
            self.FR.zero = 0

    def set_cf(self, result: int) -> None:
        '''
        Sets the Carry flag.
        
        Parameters
        ----------
        result : int
            Result of the operation.
        
        Returns
        -------
        None'''
        if result == True:
            self.FR.carry = 1
        else:
            self.FR.carry = 0

    def arithmetic_ins(self) -> None:
        '''
        Arithmetic Instructions
        -----------------------
        Instructions related to arithmetic operations in the microprocessor.
        1. ADD: Adds two numbers.
        2. ADC: Adds two numbers with previous carry.
        3. SUB: Subtracts two numbers.
        4. SBB: Subtracts two numbers with previous carry.
        5. MUL: Multiplies two numbers.
        6. DIV: Divides two numbers.
        7. INC: Increments a number.
        8. DEC: Decrements a number.
        9. CBW: Converts a number to a word.
        10. CWD: Converts a word to a number.
        '''
        if self.opcode == 'ADD':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = (res1 + res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 + res2)
            self.set_cf(((self.to_unsigned(res1) + self.to_unsigned(res2)) >> (self.opbyte * 8)) > 0)
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'ADC':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = (res1 + res2 + self.FR.carry) & int(
                "0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 + res2 + self.FR.carry)
            self.set_cf(((self.to_unsigned(res1) + self.to_unsigned(res2) + self.FR.carry) >> (self.opbyte * 8)) > 0)
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'SUB':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'SBB':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = (res1 - res2 - self.FR.carry) & int(
                "0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2 - self.FR.carry)
            if self.FR.carry == 1:
                self.set_cf(self.to_unsigned(res1) <= self.to_unsigned(res2))
            else:
                self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'MUL':
            assert self.opbyte in [1, 2]
            res2 = self.get_int(self.opd[0])
            if self.opbyte == 1:
                res1 = self.read_reg('AL')
                self.write_reg('AX', res1 * res2)
                if self.read_reg('AH') > 0:
                    self.FR.carry = self.FR.overflow = 1
                else:
                    self.FR.carry = self.FR.overflow = 0
            elif self.opbyte == 2:
                res1 = self.read_reg('AX')
                result = res1 * res2
                self.write_reg('AX', result & 0xff)
                self.write_reg('DX', (result >> 8) & 0xff)
                if self.read_reg('DX') > 0:
                    self.FR.carry = self.FR.overflow = 1
                else:
                    self.FR.carry = self.FR.overflow = 0

        elif self.opcode == 'DIV':
            assert self.opbyte in [1, 2]
            res2 = self.get_int(self.opd[0])
            if res2 == 0:
                self.interrupt_handler(0)
            elif self.opbyte == 1:
                res1 = self.read_reg('AX')
                self.write_reg('AL', res1 // res2)
                self.write_reg('AH', res1 % res2)
            elif self.opbyte == 2:
                res1 = (self.read_reg('DX') << 8) + self.read_reg('AX')
                self.write_reg('AX', res1 // res2)
                self.write_reg('DX', res1 % res2)

        elif self.opcode == 'INC':
            res1 = self.get_int(self.opd[0])
            result = (res1 + 1) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 + 1)
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'DEC':
            res1 = self.get_int(self.opd[0])
            result = (res1 - 1) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - 1)
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'CBW':
            res = self.read_reg('AL')
            if res >> 7 & 1:
                self.write_reg('AH', 255)
            else:
                self.write_reg('AH', 0)

        elif self.opcode == 'CWD':
            res = self.read_reg('AX')
            if res >> 15 & 1:
                self.write_reg('DX', 65535)
            else:
                self.write_reg('DX', 0)

        else:
            sys.exit("operation code not support")

    def logical_ins(self) -> None:
        '''
        Logical instructions
        --------------------
        Instructions that perform logical operations on operands.
        1. AND: Logical AND of two operands.
        2. OR: Logical OR of two operands.
        3. XOR: Logical XOR of two operands.
        4. NOT: Logical NOT of one operand.
        5. NEG: Logical NEGation of one operand.
        6. CMP: Compare two operands.
        7. TEST: Compare two operands without storing the result.'''
        if self.opcode == 'AND':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = res1 & res2

            self.FR.carry = self.FR.overflow = 0

            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'OR':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = res1 | res2

            self.FR.carry = self.FR.overflow = 0

            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'XOR':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = res1 ^ res2

            self.FR.carry = self.FR.overflow = 0

            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'NOT':
            res1 = self.get_int(self.opd[0])
            self.put_int(self.opd[0], ~res1)

        elif self.opcode == 'NEG':
            res1 = self.get_int(self.opd[0])
            result = ((~res1) + 1) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of((~res1) + 1)

            self.set_cf((self.to_unsigned(~res1) + 1) >> (self.opbyte * 8) > 0)

            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            self.put_int(self.opd[0], result)

        elif self.opcode == 'CMP':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

        elif self.opcode == 'TEST':
            res1 = self.get_int(self.opd[0])
            res2 = self.get_int(self.opd[1])
            result = res1 & res2

            self.FR.carry = self.FR.overflow = 0

            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

        else:
            sys.exit("operation code not support")

    def rotate_shift_ins(self) -> None:
        '''
        Rotate and shift instructions
        ----------------------------
        Instructions that perform rotate and shift operations on operands.
        1. RCL: Rotate left with the carry flag.
        2. RCR: Rotate right with the carry flag.
        3. ROL: Rotate left.
        4. ROR: Rotate right.
        5. SHL: Shift left.
        6. SHR: Shift right.
        7. SAL: Shift left.
        8. SAR: Shift right.'''
        if self.opcode == 'RCL':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = (res << 1) + self.FR.carry
                self.FR.carry = temp >> (self.opbyte * 8) & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp & int('1' * self.opbyte * 8, 2)
            self.put_int(self.opd[0], res)

        elif self.opcode == 'RCR':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = (res >> 1) + (self.FR.carry << (self.opbyte * 8 - 1))
                self.FR.carry = res & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp
            self.put_int(self.opd[0], res)

        elif self.opcode == 'ROL':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = (res << 1) + (res >> (self.opbyte * 8 - 1) & 1)
                self.FR.carry = res >> (self.opbyte * 8 - 1) & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp & int('1' * self.opbyte * 8, 2)
            self.put_int(self.opd[0], res)

        elif self.opcode == 'ROR':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = (res >> 1) + ((res & 1) << (self.opbyte * 8 - 1))
                self.FR.carry = res & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp
            self.put_int(self.opd[0], res)

        elif self.opcode == 'SAL':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = res << 1
                self.FR.carry = temp >> (self.opbyte * 8) & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == \
                    (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp & int('1' * self.opbyte * 8, 2)
            self.put_int(self.opd[0], res)

        elif self.opcode == 'SHL':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                temp = res << 1
                self.FR.carry = temp >> (self.opbyte * 8) & 1
                if (temp >> (self.opbyte * 8 - 1) & 1) == \
                    (res >> (self.opbyte * 8 - 1) & 1):
                    self.FR.overflow = 0
                else:
                    self.FR.overflow = 1
                res = temp & int('1' * self.opbyte * 8, 2)
            self.put_int(self.opd[0], res)

        elif self.opcode == 'SAR':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                self.FR.carry = res & 1
                self.FR.overflow = 0
                op = res >> (self.opbyte * 8 - 1) & 1
                res = (res >> 1) + (op << (self.opbyte * 8 - 1))
            self.put_int(self.opd[0], res)

        elif self.opcode == 'SHR':
            res = self.get_int(self.opd[0])
            cnt = self.get_int(self.opd[1])
            while cnt:
                cnt -= 1
                self.FR.carry = res & 1
                if res >> (self.opbyte * 8 - 1) & 1:
                    self.FR.overflow = 1
                else:
                    self.FR.overflow = 0
                res >>= 1
            self.put_int(self.opd[0], res)

        else:
            sys.exit("operation code not support")

    @property
    def ss_sp(self) -> int:
        '''
        Return the value of the stack pointer.
        
        Returns
        -------
        int: int
            The value of the stack pointer.
        '''
        return self.bus.reg['SS'] * 16 + self.reg['SP']

    def stack_related_ins(self) -> None:
        '''
        Stack related instructions
        --------------------------
        Instructions that manipulate the stack.
        1. PUSH: Push a value onto the stack.
        2. POP: Pop a value from the stack.
        3. PUSHF: Push the flags onto the stack.
        4. POPF: Pop the flags from the stack.'''
        if self.opcode == 'PUSH':
            self.inc_reg('SP', -2)
            self.write_mem(self.ss_sp, self.get_int(self.opd[0]))
        elif self.opcode == 'POP':
            res_list = self.bus.read_word(self.ss_sp)
            res = 0
            for num in res_list:
                res = (res << 8) + int(num, 16)
            if self.is_mem(self.opd[0]):
                ad = self.get_address(self.opd[0])
                self.write_mem(ad,res)
            elif self.is_reg(self.opd[0]):
                self.write_reg(self.opd[0], res)
            self.inc_reg('SP', 2)
        elif self.opcode == 'PUSHF':
            self.inc_reg('SP', -2)
            self.write_mem(self.ss_sp, self.FR.get_int())
        elif self.opcode == 'POPF':
            res_list = self.bus.read_word(self.ss_sp)
            res = 0
            for num in res_list:
                res = (res << 8) + int(num, 16)
            self.FR.set_int(res)
            self.inc_reg('SP', 2)
        else:
            sys.exit("operation code not support")

    def transfer_control_ins(self) -> None:
        '''
        Transfer control instructions
        -----------------------------
        Instructions that transfer control of execution to another location.
        1. JMP: Jump to a new location.
        2. LOOP: Loop till the counter is zero.
        3. LOOPE: Loop till the counter is zero and ZF is set.
        4. LOOPZ: Loop till the counter is zero and CF is set.
        5. LOOPNE: Loop till the counter is zero and ZF is clear.
        6. LOOPNZ: Loop till the counter is zero and CF is clear.
        7. CALL: Call a function.
        8. RET: Return from a function.
        9. RETF: Return from a function(far return).
        10. JA: Jump if above condition is true.
        11. JAE: Jump if above or equal condition is true.
        12. JB: Jump if below condition is true.
        13. JBE: Jump if below or equal condition is true.
        14. JC: Jump if carry condition is true.
        15. JCXZ: Jump if the counter is zero.
        16. JE: Jump if equal condition is true.
        17. JG: Jump if greater condition is true.
        18. JGE: Jump if greater or equal condition is true.
        19. JL: Jump if less condition is true.
        20. JLE: Jump if less or equal condition is true.
        21. JNA: Jump if not above condition is true.
        22. JNAE: Jump if not above or equal condition is true.
        23. JNB: Jump if not below condition is true.
        24. JNBE: Jump if not below or equal condition is true.
        25. JNC: Jump if not carry condition is true.
        26. JNE: Jump if not equal condition is true.
        27. JNG: Jump if not greater condition is true.
        28. JNGE: Jump if not greater or equal condition is true.
        29. JNL: Jump if not less condition is true.
        30. JNLE: Jump if not less or equal condition is true.
        31. JNO: Jump if not overflow condition is true.
        32. JNP: Jump if not parity condition is true.
        33. JNS: Jump if not sign condition is true.
        34. JNZ: Jump if not zero condition is true.
        35. JO: Jump if overflow condition is true.
        36. JP: Jump if parity condition is true.
        37. JPE: Jump if parity even condition is true.
        38. JS: Jump if sign condition is true.
        39. JZ: Jump if zero condition is true.'''
        
        if self.opcode == 'JMP':
            if self.is_mem(self.opd[0]):
                adr = self.get_address(self.opd[0])
                if self.opbyte == 4:
                    self.opbyte = 2
                    self.write_reg('CS', self.get_int(adr + 2))
                self.write_reg('IP', self.get_int(adr))
            elif ':' in self.opd[0]:
                self.opd = [s for s in re.split(' |:', self.opd[0]) if s]
                self.write_reg('CS', self.get_int(self.opd[0]))
                self.write_reg('IP', self.get_int(self.opd[1]))
            else:
                self.write_reg('IP', self.get_int(self.opd[0]))

        elif self.opcode == 'LOOP':
            self.inc_reg('CX', -1)
            if self.reg['CX'] != 0:
                self.write_reg('IP', self.get_int(self.opd[0]))

        elif self.opcode in ['LOOPE', 'LOOPZ']:
            self.inc_reg('CX', -1)
            if self.reg['CX'] != 0 and self.FR.zero == 1:
                self.write_reg('IP', self.get_int(self.opd[0]))

        elif self.opcode in ['LOOPNE', 'LOOPNZ']:
            self.inc_reg('CX', -1)
            if self.reg['CX'] != 0 and self.FR.zero == 0:
                self.write_reg('IP', self.get_int(self.opd[0]))

        elif self.opcode == 'CALL':
            if self.opbyte == 4 or ':' in self.opcode[0]:
                self.inc_reg('SP', -2)
                self.write_mem(self.ss_sp, self.bus.reg['CS'])
            self.inc_reg('SP', -2)
            self.write_mem(self.ss_sp, self.bus.reg['IP'])
            self.opcode = 'JMP'
            self.control_circuit()

        elif self.opcode == 'RET':
            self.write_reg('IP', self.get_int_from_adr(self.ss_sp))
            self.inc_reg('SP', 2)

        elif self.opcode == 'RETF':
            self.write_reg('IP', self.get_int_from_adr(self.ss_sp))
            self.inc_reg('SP', 2)
            self.write_reg('CS', self.get_int_from_adr(self.ss_sp))
            self.inc_reg('SP', 2)

        elif self.opcode in conditional_jump_instr:
            jmp_map = {
                'JA':  self.FR.carry == 0 and self.FR.zero == 0,
                'JAE': self.FR.carry == 0,
                'JB': self.FR.carry == 1,
                'JBE': self.FR.carry == 0 and self.FR.zero == 1,
                'JC': self.FR.carry == 1,
                'JCXZ': self.reg['CX'] == 0,
                'JE': self.FR.zero == 1,
                'JG': self.FR.zero == 0 and self.FR.sign == self.FR.overflow,
                'JGE': self.FR.sign == self.FR.overflow,
                'JL': self.FR.sign != self.FR.overflow,
                'JLE': self.FR.sign != self.FR.overflow or self.FR.zero == 1,
                'JNA': self.FR.carry == 1 or self.FR.zero == 1,
                'JNAE': self.FR.carry == 1,
                'JNB': self.FR.carry == 0,
                'JNBE': self.FR.carry == 0 and self.FR.zero == 0,
                'JNC': self.FR.carry == 0,
                'JNE': self.FR.zero == 0,
                'JNG': self.FR.zero == 1 and self.FR.sign != self.FR.overflow,
                'JNGE': self.FR.sign != self.FR.overflow,
                'JNL': self.FR.sign == self.FR.overflow,
                'JNLE': self.FR.sign == self.FR.overflow and self.FR.zero == 0,
                'JNO': self.FR.overflow == 0,
                'JNP': self.FR.parity == 0,
                'JNS': self.FR.sign == 0,
                'JNZ': self.FR.zero == 0,
                'JO': self.FR.overflow == 1,
                'JP': self.FR.parity == 1,
                'JPE': self.FR.parity == 1,
                'JPO': self.FR.parity == 0,
                'JS': self.FR.sign == 1,
                'JZ': self.FR.zero == 1
            }
            if jmp_map[self.opcode]:
                self.write_reg('IP', self.get_int(self.opd[0]))

        else:
            sys.exit("operation code not support")

    def string_manipulation_ins(self) -> None:
        '''
        String Manipulation Instructions
        --------------------------------
        Instructions that manipulate strings.
        
        1. MOVSB: Move byte from string to string.
        2. MOVSW: Move word from string to string.
        3. CMPSB: Compare byte from string to string.
        4. CMPSW: Compare word from string to string.
        5. LODSB: Load byte from string to AL.
        6. LODSW: Load word from string to AX.
        7. STOSB: Store byte from AL to string.
        8. STOSW: Store word from AX to string.
        9. SCASB: Scan byte from string to string.
        10. SCASW: Scan word from string to string.
        11. REP: Repeat string operation.
        12. REPE: Repeat string operation if equal.
        13. REPNE: Repeat string operation if not equal.
        14. REPNZ: Repeat string operation if not zero.
        15. REPZ: Repeat string operation if zero.
        '''
        if self.opcode == 'MOVSB':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res_list = self.bus.read_byte(src_adr)
            self.write_mem(dst_adr, res_list)
            if self.FR.direction == 0:
                self.inc_reg('SI', 1)
                self.inc_reg('DI', 1)
            else:
                self.inc_reg('SI', -1)
                self.inc_reg('DI', -1)

        elif self.opcode == 'MOVSW':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res_list = self.bus.read_word(src_adr)
            self.write_mem(dst_adr, res_list)
            if self.FR.direction == 0:
                self.inc_reg('SI', 2)
                self.inc_reg('DI', 2)
            else:
                self.inc_reg('SI', -2)
                self.inc_reg('DI', -2)

        elif self.opcode == 'CMPSB':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res1_list = self.bus.read_byte(src_adr)
            res1 = 0
            for num in res1_list:
                res1 = (res1 << 8) + int(num, 16)
            res2_list = self.bus.read_byte(dst_adr)
            res2 = 0
            for num in res2_list:
                res2 = (res2 << 8) + int(num, 16)

            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            if self.FR.direction == 0:
                self.inc_reg('SI', 1)
                self.inc_reg('DI', 1)
            else:
                self.inc_reg('SI', -1)
                self.inc_reg('DI', -1)

        elif self.opcode == 'CMPSW':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res1_list = self.bus.read_word(src_adr)
            res1 = 0
            for num in res1_list:
                res1 = (res1 << 8) + int(num, 16)
            res2_list = self.bus.read_word(dst_adr)
            res2 = 0
            for num in res2_list:
                res2 = (res2 << 8) + int(num, 16)

            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            if self.FR.direction == 0:
                self.inc_reg('SI', 2)
                self.inc_reg('DI', 2)
            else:
                self.inc_reg('SI', -2)
                self.inc_reg('DI', -2)

        elif self.opcode == 'LODSB':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            res_list = self.bus.read_byte(src_adr)
            res = 0
            for num in res_list:
                res = (res << 8) + int(num, 16)
            self.write_reg('AL', res)
            if self.FR.direction == 0:
                self.inc_reg('SI', 1)
            else:
                self.inc_reg('SI', -1)

        elif self.opcode == 'LODSW':
            src_adr = self.bus.reg['DS'] * 16 + self.reg['SI']
            res_list = self.bus.read_word(src_adr)
            res = 0
            for num in res_list:
                res = (res << 8) + int(num, 16)
            self.write_reg('AX', res)
            if self.FR.direction == 0:
                self.inc_reg('SI', 2)
            else:
                self.inc_reg('SI', -2)

        elif self.opcode == 'STOSB':
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res = self.read_reg('AL')
            self.bus.write_byte(dst_adr, res)
            if self.FR.direction == 0:
                self.inc_reg('DI', 1)
            else:
                self.inc_reg('DI', -1)

        elif self.opcode == 'STOSW':
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res = self.read_reg('AX')
            self.bus.write_word(dst_adr, res)
            if self.FR.direction == 0:
                self.inc_reg('DI', 2)
            else:
                self.inc_reg('DI', -2)

        elif self.opcode == 'SCASB':
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res1 = self.read_reg('AL')
            res2_list = self.bus.read_byte(dst_adr)
            res2 = 0
            for num in res2_list:
                res2 = (res2 << 8) + int(num, 16)

            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            if self.FR.direction == 0:
                self.inc_reg('DI', 1)
            else:
                self.inc_reg('DI', -1)

        elif self.opcode == 'SCASW':
            dst_adr = self.bus.reg['ES'] * 16 + self.reg['DI']
            res1 = self.read_reg('AX')
            res2_list = self.bus.read_word(dst_adr)
            res2 = 0
            for num in res2_list:
                res2 = (res2 << 8) + int(num, 16)

            result = (res1 - res2) & int("0x" + "f" * self.opbyte * 2, 16)

            self.set_of(res1 - res2)
            self.set_cf(self.to_unsigned(res1) < self.to_unsigned(res2))
            self.set_pf(result)
            self.set_zf(result)
            self.set_sf(result)

            if self.FR.direction == 0:
                self.inc_reg('DI', 2)
            else:
                self.inc_reg('DI', -2)

        elif self.opcode == 'REP':
            self.opcode = self.opd[0]
            if len(self.opd) > 1:
                self.opd = self.opd[1:]
            else:
                self.opd = []
            self.get_opbyte()
            
            while self.read_reg('CX') != 0:
                self.control_circuit()
                res = self.read_reg('CX')
                self.write_reg('CX', res - 1)

        elif self.opcode == 'REPE':
            self.opcode = self.opd[0]
            if len(self.opd) > 1:
                self.opd = self.opd[1:]
            else:
                self.opd = []
            self.get_opbyte()
            while self.read_reg('CX') != 0:
                self.control_circuit()
                res = self.read_reg('CX')
                self.write_reg('CX', res - 1)
                if self.FR.zero == 0:
                    break

        elif self.opcode == 'REPZ':
            self.opcode = self.opd[0]
            if len(self.opd) > 1:
                self.opd = self.opd[1:]
            else:
                self.opd = []
            self.get_opbyte()
            while self.read_reg('CX') != 0:
                self.control_circuit()
                res = self.read_reg('CX')
                self.write_reg('CX', res - 1)
                if self.FR.zero == 0:
                    break

        elif self.opcode == 'REPNE':
            self.opcode = self.opd[0]
            if len(self.opd) > 1:
                self.opd = self.opd[1:]
            else:
                self.opd = []
            self.get_opbyte()
            while self.read_reg('CX') != 0:
                self.control_circuit()
                res = self.read_reg('CX')
                self.write_reg('CX', res - 1)
                if self.FR.zero == 1:
                    break

        elif self.opcode == 'REPNZ':
            self.opcode = self.opd[0]
            if len(self.opd) > 1:
                self.opd = self.opd[1:]
            else:
                self.opd = []
            self.get_opbyte()
            while self.read_reg('CX') != 0:
                self.control_circuit()
                res = self.read_reg('CX')
                self.write_reg('CX', res - 1)
                if self.FR.zero == 1:
                    break

        else:
            sys.exit("operation code not support")

    def flag_manipulation_ins(self) -> None:
        '''
        Flag Manipulation Instructions
        ------------------------------
        
        Instructions that manipulate the status flags.
        
        1. STC: Set Carry Flag.
        2. CLC: Clear Carry Flag.
        3. CMC: Complement Carry Flag.
        4. STD: Set Direction Flag.
        5. CLD: Clear Direction Flag.
        6. STI: Set Interrupt Flag.
        7. CLI: Clear Interrupt Flag.
        8. LANF: Load Accumulator with Flag.
        9. SANF: Store Accumulator with Flag.'''
        if self.opcode == 'STC':
            self.FR.carry = 1
        elif self.opcode == 'CLC':
            self.FR.carry = 0
        elif self.opcode == 'CMC':
            self.FR.carry ^= 1
        elif self.opcode == 'STD':
            self.FR.direction = 1
        elif self.opcode == 'CLD':
            self.FR.direction = 0
        elif self.opcode == 'STI':
            self.FR.interrupt = 1
        elif self.opcode == 'CLI':
            self.FR.interrupt = 0
        elif self.opcode == 'LANF':
            self.write_reg('AH', self.FR.get_low())
        elif self.opcode == 'SANF':
            self.FR.set_low(self.read_reg('AH'))
        else:
            sys.exit("operation code not support")

    def input_output_ins(self) -> None:
        '''
        Input/Output Instructions
        --------------------------
        
        Instructions that read or write to memory.
        
        1. IN: Read from port.
        2. OUT: Write to port.'''
        if self.opcode == 'IN':
            port = to_decimal(self.opd[1])
            val = to_decimal(input(f"Input to Port {port}: "))
            self.write_reg(self.opd[0], val)
        elif self.opcode == 'OUT':
            port = self.get_int(self.opd[0])
            val = self.read_reg(self.opd[1])
            self.print("> " * 16 + "@Port {}: 0x{:<4x} => {}\n".format(port, val, val))
        else:
            sys.exit("operation code not support")

    def dos_isr_21h(self) -> None:
        '''
        DOS Interrupt 21h
        -----------------
        
        The DOS interrupt 21h is used to set the interrupt vector table.
        The interrupt vector table is a table of 16-bit addresses that
        contain the addresses of the interrupt service routines.
        The interrupt vector table is located at offset 0x4 in the BIOS
        data area.
        The interrupt vector table is initialized to point to the BIOS
        interrupt service routines.
        
        Interrupt Types
        ---------------
        0x0: Reset
        0x01: Read character from stdin
        0x02: Write character to stdout
        0x09: Write string to stdout
        0x2A: Get system date
        0x2C: Get system time
        0x35: Get interrupt vector
        0x4C: Exit program
        '''
        ah = self.read_reg('AH')
        al = self.read_reg('AL')
        if self.int_msg:
            self.print(f"\nDOS Interrupt 21H, AH={hex(ah)}\n")
        if ah == 0x0:
            if self.int_msg:
                self.print("Reset\n")
            self.print("> " * 16 + "Exit to operating system")
            self.shutdown = True

        elif ah == 0x01:
            if self.int_msg:
                self.print("Read character from STDIN\n")
            char = input()[0]
            self.write_reg('AL', ord(char))
        
        elif ah == 0x02:
            if self.int_msg:
                self.print("Write character to STDOUT\n")
            char = chr(self.read_reg('DL'))
            self.print('> '+ char + '\n')

        elif ah == 0x9:
            if self.int_msg:
                self.print("Write string to STDOUT\n")
            address = (self.read_reg('DS') << 4) + self.read_reg('DX')
            count = 0
            self.print("> " * 16)

            while True:
                char = self.__get_char(address)
                if char == '$' or count == 500:
                    break
                self.print(char)
                address += 1
                count += 1
            self.print('\n')

        elif ah == 0x2a:
            if self.int_msg:
                self.print("Get System Date\n")
            now = datetime.datetime.now()
            self.write_reg('CX', now.year)
            self.write_reg('DH', now.month)
            self.write_reg('DL', now.day)

        elif ah == 0x2c:
            if self.int_msg:
                self.print("Get system time\n")
            now = datetime.datetime.now()
            self.write_reg('CH', now.hour)
            self.write_reg('CL', now.minute)
            self.write_reg('DH', now.second)
            self.write_reg('DL', int(now.microsecond * 1e4))
        
        elif ah == 0x35:
            if self.int_msg:
                self.print("Get interrupt vector\n")
            int_type = self.read_reg('AL')
            self.write_reg('BX', self.get_int_from_adr(int_type * 4))
            self.write_reg('ES', self.get_int_from_adr(int_type * 4 + 2))
        
        elif ah == 0x4c:
            if self.int_msg:
                self.print("Exiting program\n")
            self.print(f"\nExit with return code {al}\n")
            self.shutdown = True

        else:
            sys.exit("Interrupt Error")

    def bios_isr_10h(self) -> None:
        '''
        BIOS Interrupt 10h'''
        pass

    def interrupt_handler(self, int_type: int) -> None:
        '''
        Interrupt Handler
        -----------------
        
        The interrupt handler is the routine that is called when an
        interrupt occurs.
        
        The interrupt handler is called by the interrupt service routine
        and is responsible for setting the correct interrupt vector and
        calling the appropriate interrupt service routine.
        
        Parameters
        ----------
        int_type : int
            The interrupt type.
        
        Returns
        -------
        None'''
        self.inc_reg('SP', -2)
        self.write_mem(self.ss_sp, self.FR.get_int())
        self.FR.trap = 0
        self.FR.interrupt = 0
        self.inc_reg('SP', -2)
        self.write_mem(self.ss_sp, self.get_int('CS'))
        self.inc_reg('SP', -2)
        self.write_mem(self.ss_sp, self.get_int('IP'))
        self.opbyte = 2
        ip_val = self.get_int_from_adr(int_type * 4)
        cs_val = self.get_int_from_adr(int_type * 4 + 2)
        self.write_reg('IP', ip_val)
        self.write_reg('CS', cs_val)
        if self.int_msg:
            self.print(f'Execute {hex(int_type)} interrupt...')
            self.print('Interrupt processed...')
            self.print(f'Reading Interrupt Vector Table {hex(int_type) * 4}, offset {hex(ip_val)} => IP\n...')
            self.print(f'Reading Interrupt Vector Table {hex(int_type) * 4 + 2}, offset {hex(cs_val)} => CS\n...')
            self.print('Entered interrupt routine...')

    def miscellaneous_ins(self) -> None:
        '''
        Miscellaneous Instructions
        -------------------------
        
        The following instructions are used to perform miscellaneous
        tasks.
        
        1. NOP: No operation
        2. INT: Interrupt request
        3. IRET: Interrupt return
        4. XLAT: Translate address
        5. ESC: Escape to protected mode
        6. WAIT: Wait for interrupt
        7. HLT: Halt
        8. INTO: Overflow trap
        9. LOCK: Set LOCK bit''' 
        if self.opcode == 'NOP':
            pass
        elif self.opcode == 'INT':
            if not self.opd:
                self.print("\Interrupt without a value\n")
                self.interrupt = True
            else:
                int_type = to_decimal(self.opd[0])
                if int_type == 3:
                    self.print("\nBreak-Point Interrupt.\n")
                    self.interrupt = True
                elif int_type == to_decimal('10H'):
                    self.bios_isr_10h()
                elif int_type == to_decimal('21H'):
                    self.dos_isr_21h()
                elif int_type in [to_decimal(i) for i in ['7ch']]:
                    self.interrupt_handler(int_type)
                else:
                    sys.exit("Interrupt Type Error")

        elif self.opcode == 'IRET':
            if self.int_msg:
                self.print("Interrupt routine ended...\n")
            self.opcode = 'POP'
            self.opd = ['IP']
            self.control_circuit()

            self.opcode = 'POP'
            self.opd = ['CS']
            self.control_circuit()

            self.opcode = 'POPF'
            self.control_circuit()
            if self.int_msg:
                self.print("Recovery from interrupt successful.\n")

        elif self.opcode == 'XLAT':
            pass
        elif self.opcode == 'HLT':
            self.shutdown = True
        elif self.opcode == 'ESC':
            pass
        elif self.opcode == 'INTO':
            if self.FR.overflow:
                self.interrupt_handler(4)
        elif self.opcode == 'LOCK':
            pass
        elif self.opcode == 'WAIT':
            pass
        else:
            sys.exit("operation code not support")