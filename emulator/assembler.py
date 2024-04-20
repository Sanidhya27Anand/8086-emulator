from __future__ import annotations

import re
import os
import sys
import ast

from typing import Optional

from emulator.instructions import transfer_control_instr, data_definition_instr

def create_int_str(matched: re.Match) -> str:
    '''
    Create a string of integers from a regex match.
    
    Parameters
    ----------
    matched : re.Match
        The match object.
    
    Returns
    -------
    int_str : str
        The string of integers.
    '''
    string = matched.group()
    idx = re.search(r'[,\s\]]', string).span()[0]
    suffix = string[idx:]
    string = string[:idx]
    int_str = str(to_decimal(string))
    return int_str + suffix

def to_decimal(num: str) -> int:
    '''
    Convert a string of integers to a decimal integer.
    
    Parameters
    ----------
    num : str
        The string of integers.
    
    Returns
    -------
    decimal : int
        The decimal integer.
    '''
    if isinstance(num, int):
        return int(num)
    if num.startswith('0x'):
        return int(num, 16)
    if num.startswith('0X'):
        return int(num[2:], 16)
    num = num.upper()
    if num[-1] == 'B':
        res = int(num.rstrip('B'), 2)
    elif num[-1] == 'O':
        res = int(num.rstrip('O'), 8)
    elif num[-1] == 'D':
        res = int(num.rstrip('D'), 10)
    elif num[-1] == 'H':
        res = int(num.rstrip('H'), 16)
    else:
        res = int(num)
    return res

class Assembler(object):
    '''
    The `Assembler` class for preprocessing and compiling of the code. Internally acts like an interpreter,\
    but does the work of the 8086 assembler.'''
    def __init__(self, seg: dict) -> None:
        self.name = ''                      # name of the program
        self.title = ''                     # title of the program
        self.space = {}                     # segment space for the program
        self.segment_address = {'DS': hex(seg['DS']), 'CS': hex(seg['CS']), 'SS': hex(seg['SS']), 'ES': hex(seg['ES'])}     # default segment addresses for the program
        self.segment_id = {}                    # segment ids for the program
        self.segment_length = {}                # segment lengths for the program
        self.tags = {}                          # tags for the program
        self.vars = {}                          # variables for the program
        self.instr_ptr = '0'                    # instruction pointer
        self.instr_origin = []                    # instruction origin

    def compile(self, code: str) -> Assembler:
        '''
        Function to compile the code.
        
        Parameters
        ----------
        code : str
            The code to be compiled.
        
        Returns
        -------
        self : Assembler
            The assembler object.
        '''
        instructions = self.__preprocessing(code)
        for instr_ptr in range(len(instructions)):
            instr = instructions[instr_ptr]
            if instr[0] == 'NAME':
                self.name = instr[1] 
            elif instr[0] == 'TITLE':
                self.title = instr[1]
            elif instr[0] == 'ASSUME':
                self.__assume(instr[1:])
            elif len(instr) > 1 and instr[1] == 'SEGMENT':
                instr_ptr = self.__segment(instructions, instr_ptr)
            elif instr[0] == 'END':
                self.instr_ptr = self.tags[instr[1]]['offset']

        self.__eval_id()

        return self

    def __eval_id(self) -> None:
        '''
        Function to evaluate the segment ids.
        
        Returns
        -------
        None
        '''
        var_dict = {}
        for key, val in self.segment_id.items():
            var_dict[key] = str(self.segment_address[val])
        for key, val in self.vars.items():
            for k, v in self.segment_address.items():
                if v == val['seg']:
                    seg_name = k
            var_dict[key] = seg_name + ':[' + str(hex(int(val['offset'], 16))) + ']'
        for key, val in self.space.items():
            for i in range(len(self.space[key])):
                instr = self.space[key][i]
                if instr:
                    if instr[0] in transfer_control_instr and instr[-1] in self.tags.keys():
                        for s in ['SHORT', 'NEAR', 'PTR']:
                            if s in instr:
                                self.space[key][i].remove(s)
                        if instr[1] == 'FAR':
                            self.space[key][i].remove('FAR')
                            dst = self.tags[instr[1]]['seg'] + ':' + self.tags[instr[1]]['offset']
                            self.space[key][i][1] = dst
                        else:
                            self.space[key][i][1] = self.tags[instr[1]]['offset']
                    j = 0
                    while j < len(instr):
                        for s in ['SEG', 'OFFSET', 'TYPE']:
                            if instr[j] == s:
                                self.space[key][i].remove(s)
                                if instr[j] in self.vars.keys():
                                    self.space[key][i][j] = self.vars[instr[j]][s.lower()] 
                                else:
                                    self.space[key][i][j] = self.tags[instr[j]][s.lower()] 
                        for k, v in var_dict.items():
                            if instr[j] == k:
                                self.space[key][i][j] = v
                            elif instr[j][:len(k)] == k and instr[j][len(k)] == '[':
                                self.space[key][i][j] = v + instr[j][len(k):]
                        j += 1

    def __segment(self, instructions: list, instr_ptr: int) -> Optional[int]:
        '''
        Function to process the segment space.
        
        Parameters
        ----------
        instructions : list
            The list of instructions.
        instr_ptr : int
            The index of the instruction pointer.
        
        Returns
        -------
        instr_ptr : Optional[int]
            The index of the instruction pointer.'''
        segment_instr_ptr = 0
        seg_ins = instructions[instr_ptr]
        seg_tmp = seg_ins[0]
        seg_name = self.segment_id[seg_tmp]
        self.space[seg_name] = [['0']] * int('10000', 16)
        for i in range(instr_ptr+1, len(instructions)):
            instr = instructions[i]
            for j in range(len(instr)):
                if instr[j] == '$':
                    instr[j] == str(hex(segment_instr_ptr))
            ins_ori = self.instr_origin[i]
            if instr[0] == 'ORG':
                segment_instr_ptr = to_decimal(instr[1])
            elif instr[0] == 'EVEN':
                segment_instr_ptr += segment_instr_ptr % 2
            elif instr[0] == 'ALIGN':
                num = to_decimal(instr[1])
                assert num & (num-1) == 0, "Num should be power of 2"
                segment_instr_ptr += (-segment_instr_ptr) % num 
            elif instr[0] == seg_tmp:
                assert instr[1] == 'ENDS', "Compile Error: segment ends fault"
                self.segment_length[seg_name] = segment_instr_ptr
                return i + 1

            elif ':' in instr[0]:
                tag_list = instr[0].split(':')
                tag = tag_list[0]
                self.tags[tag] = {'seg': self.segment_address[seg_name],
                                  'offset': hex(segment_instr_ptr),
                                  'type': 0}
                if len(instr) == 1:
                    pass
                else:
                    if tag_list[1]:
                        instr[0] = tag_list[1]
                    else:
                        instr = instr[1:]
                    self.space[seg_name][segment_instr_ptr] = instr
                    segment_instr_ptr += 1
            
            elif instr[0] in data_definition_instr:
                byte_list = self.__data_define(instr, ins_ori)
                self.space[seg_name][segment_instr_ptr:segment_instr_ptr+len(byte_list)] = byte_list
                segment_instr_ptr += len(byte_list)
            elif len(instr) > 2 and instr[1] in data_definition_instr:
                var = instr[0]
                self.vars[var] = {'seg': self.segment_address[seg_name],
                                  'offset': hex(segment_instr_ptr),
                                  'type': 0}
                var_ori = ins_ori.split()[0]
                byte_list = self.__data_define(instr[1:], ins_ori.replace(var_ori, '', 1).strip())
                self.space[seg_name][segment_instr_ptr:segment_instr_ptr+len(byte_list)] = byte_list
                segment_instr_ptr += len(byte_list)
            else:
                self.space[seg_name][segment_instr_ptr] = instr
                segment_instr_ptr += 1

    def __data_define(self, instr: list, ins_ori: str) -> list:
        '''
        Function to process the data definition.
        
        Parameters
        ----------
        instr : list
            The list of instructions.
        ins_ori : str
            The original instruction.
        '''
        var = instr[0]
        var_ori = ins_ori.split()[0]
        byte_list = []

        if len(instr) > 2 and instr[2][:3] == 'DUP':
            times = to_decimal(instr[1])
            idx = ins_ori.find('(')
            dup_str = var + ' ' + ins_ori[idx + 1:-1]
            dup_list = [s for s in re.split(" |,", dup_str.strip().upper()) if s]
            byte_list = self.__data_define(dup_list, dup_str) * times

        elif var == 'DB':
            db_str = ins_ori.replace(var_ori, '', 1).strip()
            byte_list = self.__str_to_bytes(db_str)

        elif var == 'DW':
            dw_str = ins_ori.replace(var_ori, '', 1).strip()
            byte_list = self.__str_to_words(dw_str)

        elif var == 'DD':
            dd_str = ins_ori.replace(var_ori, '', 1).strip()
            byte_list = self.__str_to_dwords(dd_str)
            
        else:
            sys.exit("Compile Error")
        
        return byte_list

    @classmethod
    def __str_to_bytes(cls, string: str) -> list:
        '''
        Function to convert string to bytes.
        
        Parameters
        ----------
        string : str
            The string to be converted.
        
        Returns
        -------
        byte_list : list
            The list of bytes.
        '''
        string = re.sub(r"[0-9A-Fa-f]+[HhBbOo]{1}[,\s\]]+", create_int_str, '[' + string + ']')
        str_list =  ast.literal_eval(string)
        byte_list = []
        for item in str_list:
            if isinstance(item, int):
                byte_list.append([hex(item)])
            elif isinstance(item, str):
                for s in item:
                    byte_list.append([hex(ord(s))])
            else:
                sys.exit("Compile Error: str to hex")
        return byte_list

    @classmethod
    def __str_to_words(cls, string: str) -> list:
        '''
        Function to convert string to words.

        Parameters
        ----------
        string : str
            The string to be converted.
        
        Returns
        -------
        word_list : list
            The list of words.
        '''
        string = re.sub(r"[0-9A-Fa-f]+[HhBbOo]{1}[,\s\]]+", create_int_str, '[' + string + ']')
        str_list =  ast.literal_eval(string)
        byte_list = []
        for item in str_list:
            assert isinstance(item, int), "Compile Error: str to hex"
            high, low = item >> 8, item & 0x0ff
            byte_list.append([hex(low)])
            byte_list.append([hex(high)]) 
        return byte_list

    @classmethod
    def __str_to_dwords(cls, string: str) -> list:
        '''
        Function to convert string to dwords.
        
        Parameters
        ----------
        string : str
            The string to be converted.
        
        Returns
        -------
        dword_list : list
            The list of dwords.
        ''' 
        string = re.sub(r"[0-9A-F]+[HhBbOo]{1}[,\s\]]+", create_int_str, '[' + string + ']')
        str_list =  ast.literal_eval(string)
        byte_list = []
        for item in str_list:
            assert isinstance(item, int), "Compile Error: str to hex"
            byte_list.append([hex(item & 0x0ff)])
            byte_list.append([hex(item >> 8 & 0x0ff)])
            byte_list.append([hex(item >> 16 & 0x0ff)])
            byte_list.append([hex(item >> 24)])
        return byte_list

    def __assume(self, instr: list) -> None:
        '''
        Function to process the assume instruction.
        
        Parameters
        ----------
        instr : list
            The list of instructions.
        
        Returns
        -------
        None
        '''
        for i in instr:
            i = i.split(':')
            self.segment_id[i[1]] = i[0]

    def __strip_comments(self, text: str) -> str:
        '''
        Function to strip comments.

        Parameters
        ----------
        text : str
            The text to be stripped.
        
        Returns
        -------
        text : str
            The stripped text.
        '''        
        return re.sub(r'(?m) *;.*n?', '', str(text))

    def __remove_empty_line(self, text: str) -> str:
        '''
        Function to remove empty lines.
        
        Parameters
        ----------
        text : str
            The text to be removed.
        
        Returns
        -------
        text : str
            The removed text.
        '''
        return os.linesep.join([s.strip() for s in text.splitlines() if s.strip()])

    def __preprocessing(self, code: str) -> list:
        ''''
        Function to preprocess the code.
        
        Parameters
        ----------
        code : str
            The code to be preprocessed.
        
        Returns
        -------
        instructions : list
            A list of instructions.'''
        code = self.__strip_comments(code)
        code = self.__remove_empty_line(code)
        code = code.replace('?', '0')
        instructions = []
        for line in code.split(os.linesep):
            instructions.append([s for s in re.split(" |,", line.strip().upper()) if s])
            self.instr_origin.append(line.strip())

        return instructions