class FlagRegister(object):
    '''
    The 8086 Flag Register
    ----------------------
    The flag register is a 16-bit register that contains the condition codes for the last executed instruction.
    The flag register is updated by the CPU after each instruction.
    '''
    def __init__(self) -> None:
        # status flags
        self.sign = 0       # Sign Flag
        self.zero = 0       # Zero Flag
        self.auxiliary = 0  # Auxiliary Carry Flag
        self.parity = 0     # Parity Flag
        self.carry = 0      # Carry Flag
        self.overflow = 0   # Overflow Flag
        # control flags
        self.direction = 0  # Direction Flag
        self.interrupt = 0  # Interrupt Flag
        self.trap = 0       # Trap Flag
    
    def get_int(self) -> int:
        '''
        Returns the value of the flag register as an integer.
        
        Returns
        -------
        int: int
            The value of the flag register.'''
        return (self.overflow << 11) + (self.direction << 10) + (self.interrupt << 9) + \
            (self.trap << 8) + (self.sign << 7) + (self.zero << 6) + (self.auxiliary << 4) + \
                (self.parity << 2) + (self.carry)

    def get_low(self) -> int:
        '''
        Returns the value of the flag register as an integer.
        
        Returns
        -------
        int: int
            The value of the flag register.'''
        return self.get_int() & 0xff

    def set_low(self, num: int) -> None:
        '''
        Sets the value of the flag register.
        
        Parameters
        ----------
        num: int
            The value of the flag register.
        
        Returns
        -------
        None'''
        self.sign = num >> 7 & 1
        self.zero = num >> 6 & 1
        self.auxiliary = num >> 4 & 1
        self.parity = num >> 2 & 1
        self.carry = num & 1

    def set_int(self, num: int) -> None:
        '''
        Sets the value of the flag register.
        
        Parameters
        ----------
        num: int
            The value of the flag register.
        
        Returns
        -------
        None'''
        self.set_low(num & 0xff)
        self.overflow = num >> 11 & 1
        self.direction = num >> 10 & 1
        self.interrupt = num >> 9 & 1
        self.trap = num >> 8 & 1

    def get_FR_reg(self, name: str) -> int:
        '''
        Returns the value of the flag register.
        
        Parameters
        ----------
        name: str
            The name of the flag register.
        
        Returns
        -------
        int: int
            The value of the flag register.'''
        self.reg = {
            'CF': self.carry,
            'PF': self.parity,
            'AF': self.auxiliary,
            'Z': self.zero,
            'S': self.sign,
            'O': self.overflow,
            'TF': self.trap,
            'IF': self.interrupt,
            'DF': self.direction
        }
        return self.reg[name]